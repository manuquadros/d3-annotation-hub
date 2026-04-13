<script lang="ts">
    import { invalidateAll } from "$app/navigation";
    import { browser } from "$app/environment";
    import { untrack } from "svelte";
    import type { PageData } from "./$types";
    import type { PointerOut, RelationOut } from "./+page.server";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();

    const {
        reference,
        entities: initialEntities,
        snapshots,
        curated_pointers,
        curated_relations,
    } = untrack(() => data.data);

    // ---------------------------------------------------------------------------
    // Plain-text extraction from the HTML body (client-side only)
    // ---------------------------------------------------------------------------

    let plainText = $derived(
        browser && reference.body
            ? (() => {
                  const doc = new DOMParser().parseFromString(
                      reference.body!,
                      "text/html",
                  );
                  return doc.body.textContent ?? "";
              })()
            : "",
    );

    function getAnnotatedText(offset: number, length: number): string {
        if (!plainText) return "";
        return plainText.slice(offset, offset + length);
    }

    // ---------------------------------------------------------------------------
    // Entity state (mutable so CURIE edits can update local keys)
    // ---------------------------------------------------------------------------

    let entities = $state({ ...initialEntities });

    // ---------------------------------------------------------------------------
    // Build unique pointer map: key = "entity_id|offset|length"
    // ---------------------------------------------------------------------------

    type PointerKey = string;
    function pointerKey(p: PointerOut): PointerKey {
        return `${p.entity_id}|${p.offset}|${p.length}`;
    }

    const pointerAnnotators = new Map<PointerKey, Set<string>>();
    const pointerData = new Map<PointerKey, PointerOut>();

    for (const snap of snapshots) {
        for (const p of snap.pointers) {
            const k = pointerKey(p);
            if (!pointerAnnotators.has(k)) {
                pointerAnnotators.set(k, new Set());
                pointerData.set(k, p);
            }
            pointerAnnotators.get(k)!.add(snap.email);
        }
    }

    // ---------------------------------------------------------------------------
    // Build unique entity map: entity_id → set of annotators who used it
    // ---------------------------------------------------------------------------

    const entityAnnotators = new Map<string, Set<string>>();
    for (const snap of snapshots) {
        for (const p of snap.pointers) {
            if (!entityAnnotators.has(p.entity_id)) {
                entityAnnotators.set(p.entity_id, new Set());
            }
            entityAnnotators.get(p.entity_id)!.add(snap.email);
        }
    }

    // ---------------------------------------------------------------------------
    // Build unique relations
    // ---------------------------------------------------------------------------

    type RelationKey = string;
    function relationKey(r: RelationOut): RelationKey {
        return `${r.predicate}|${r.subject}|${r.object}`;
    }

    const relationAnnotators = new Map<RelationKey, Set<string>>();
    const relationData = new Map<RelationKey, RelationOut>();

    for (const snap of snapshots) {
        for (const r of snap.relations) {
            const k = relationKey(r);
            if (!relationAnnotators.has(k)) {
                relationAnnotators.set(k, new Set());
                relationData.set(k, r);
            }
            relationAnnotators.get(k)!.add(snap.email);
        }
    }

    // ---------------------------------------------------------------------------
    // Text panel: split plain text into segments at pointer boundaries
    // (must be after pointerAnnotators / pointerData are populated)
    // ---------------------------------------------------------------------------

    // Spans sorted by offset for linear text rendering
    const spansByOffset = [...pointerAnnotators.keys()]
        .map((k) => ({ key: k, p: pointerData.get(k)! }))
        .sort((a, b) => a.p.offset - b.p.offset || b.p.length - a.p.length);

    const spanIndexByKey = new Map(spansByOffset.map((s, i) => [s.key, i]));

    interface TextSeg {
        text: string;
        key: PointerKey | null;
        idx: number;
    }

    let textSegments = $derived.by((): TextSeg[] => {
        if (!plainText) return [];
        const segs: TextSeg[] = [];
        let pos = 0;
        for (const { key, p } of spansByOffset) {
            if (p.offset >= plainText.length) break;
            if (p.offset > pos) {
                segs.push({
                    text: plainText.slice(pos, p.offset),
                    key: null,
                    idx: -1,
                });
            }
            if (p.offset >= pos) {
                const end = Math.min(p.offset + p.length, plainText.length);
                segs.push({
                    text: plainText.slice(p.offset, end),
                    key,
                    idx: spanIndexByKey.get(key)!,
                });
                pos = end;
            }
            // overlapping span: skip
        }
        if (pos < plainText.length) {
            segs.push({ text: plainText.slice(pos), key: null, idx: -1 });
        }
        return segs;
    });

    // Active pointer (set by clicking a row → scrolls text panel to the span)
    let activePointerKey = $state<PointerKey | null>(null);

    function focusPointer(k: PointerKey) {
        activePointerKey = k;
        const idx = spanIndexByKey.get(k);
        if (idx !== undefined) {
            document
                .getElementById(`pspan-${idx}`)
                ?.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    // ---------------------------------------------------------------------------
    // Accepted keys from previously saved curated annotation
    // (must be declared before the sort computations below)
    // ---------------------------------------------------------------------------

    const acceptedPointerKeys = new Set<PointerKey>(
        curated_pointers.map((p) => pointerKey(p)),
    );

    const acceptedRelationKeys = new Set<RelationKey>(
        curated_relations.map((r) => relationKey(r)),
    );

    // Accepted entity ids: any entity that appears in an accepted pointer
    const acceptedEntityIds = new Set<string>(
        curated_pointers.map((p) => p.entity_id),
    );

    // ---------------------------------------------------------------------------
    // Sorted keys (reference accepted* sets declared above)
    // ---------------------------------------------------------------------------

    const sortedPointerKeys = [...pointerAnnotators.keys()].sort((a, b) => {
        // Accepted pointers go to the bottom
        const aAccepted = acceptedPointerKeys.has(a) ? 1 : 0;
        const bAccepted = acceptedPointerKeys.has(b) ? 1 : 0;
        if (aAccepted !== bAccepted) return aAccepted - bAccepted;
        const countDiff =
            pointerAnnotators.get(b)!.size - pointerAnnotators.get(a)!.size;
        if (countDiff !== 0) return countDiff;
        const nameA =
            entities[pointerData.get(a)!.entity_id]?.preferred_name ?? a;
        const nameB =
            entities[pointerData.get(b)!.entity_id]?.preferred_name ?? b;
        return nameA.localeCompare(nameB);
    });

    const sortedEntityIds = [...entityAnnotators.keys()].sort((a, b) => {
        // Accepted entities go to the bottom
        const aAccepted = acceptedEntityIds.has(a) ? 1 : 0;
        const bAccepted = acceptedEntityIds.has(b) ? 1 : 0;
        if (aAccepted !== bAccepted) return aAccepted - bAccepted;
        const countDiff =
            entityAnnotators.get(b)!.size - entityAnnotators.get(a)!.size;
        if (countDiff !== 0) return countDiff;
        return (entities[a]?.preferred_name ?? a).localeCompare(
            entities[b]?.preferred_name ?? b,
        );
    });

    const sortedRelationKeys = [...relationAnnotators.keys()].sort((a, b) => {
        const aAccepted = acceptedRelationKeys.has(a) ? 1 : 0;
        const bAccepted = acceptedRelationKeys.has(b) ? 1 : 0;
        if (aAccepted !== bAccepted) return aAccepted - bAccepted;
        return (
            relationAnnotators.get(b)!.size - relationAnnotators.get(a)!.size
        );
    });

    // ---------------------------------------------------------------------------
    // Pointer/relation selection state
    // Pre-select from saved curation if available, otherwise unanimous agreement
    // ---------------------------------------------------------------------------

    const hasSavedCuration =
        acceptedPointerKeys.size > 0 || acceptedRelationKeys.size > 0;

    let selectedPointers = $state<Set<PointerKey>>(
        new Set(
            hasSavedCuration
                ? sortedPointerKeys.filter((k) => acceptedPointerKeys.has(k))
                : sortedPointerKeys.filter(
                      (k) =>
                          pointerAnnotators.get(k)!.size === snapshots.length &&
                          snapshots.length > 0,
                  ),
        ),
    );
    let selectedRelations = $state<Set<RelationKey>>(
        new Set(
            hasSavedCuration
                ? sortedRelationKeys.filter((k) => acceptedRelationKeys.has(k))
                : sortedRelationKeys.filter(
                      (k) =>
                          relationAnnotators.get(k)!.size ===
                              snapshots.length && snapshots.length > 0,
                  ),
        ),
    );

    function togglePointer(k: PointerKey) {
        const next = new Set(selectedPointers);
        if (next.has(k)) next.delete(k);
        else next.add(k);
        selectedPointers = next;
    }

    function toggleRelation(k: RelationKey) {
        const next = new Set(selectedRelations);
        if (next.has(k)) next.delete(k);
        else next.add(k);
        selectedRelations = next;
    }

    // An entity is "accepted" when every one of its pointer keys is selected.
    function isEntityAccepted(entityId: string): boolean {
        const keys = sortedPointerKeys.filter(
            (k) => pointerData.get(k)!.entity_id === entityId,
        );
        return keys.length > 0 && keys.every((k) => selectedPointers.has(k));
    }

    function toggleEntity(entityId: string) {
        const keys = sortedPointerKeys.filter(
            (k) => pointerData.get(k)!.entity_id === entityId,
        );
        const accepted = isEntityAccepted(entityId);
        const next = new Set(selectedPointers);
        if (accepted) {
            keys.forEach((k) => next.delete(k));
        } else {
            keys.forEach((k) => next.add(k));
        }
        selectedPointers = next;
    }

    // ---------------------------------------------------------------------------
    // CURIE editing for proposed entities
    // ---------------------------------------------------------------------------

    let curieEdits = $state(new Map<string, string>());
    let curieErrors = $state(new Map<string, string>());
    let curieSaving = $state(new Set<string>());

    function startCurieEdit(entityId: string) {
        if (!curieEdits.has(entityId)) {
            curieEdits = new Map(curieEdits).set(entityId, entityId);
        }
    }

    async function applyCurieEdit(entityId: string) {
        const newCurie = curieEdits.get(entityId)?.trim();
        if (!newCurie || newCurie === entityId) {
            curieEdits = new Map(curieEdits);
            curieEdits.delete(entityId);
            return;
        }

        curieSaving = new Set(curieSaving).add(entityId);
        curieErrors = new Map(curieErrors);
        curieErrors.delete(entityId);

        try {
            const res = await fetch(
                `/api/projects/${data.projectId}/curation/entity-curie?curie=${encodeURIComponent(entityId)}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ new_curie: newCurie }),
                },
            );
            if (!res.ok) {
                const text = await res.text();
                curieErrors = new Map(curieErrors).set(
                    entityId,
                    text || "Failed",
                );
            } else {
                await invalidateAll();
            }
        } catch (e) {
            curieErrors = new Map(curieErrors).set(entityId, String(e));
        } finally {
            curieSaving = new Set(curieSaving);
            curieSaving.delete(entityId);
        }
    }

    // ---------------------------------------------------------------------------
    // Save curated annotation
    // ---------------------------------------------------------------------------

    let saving = $state(false);
    let saveError = $state<string | null>(null);
    let saved = $state(false);

    async function saveCuration() {
        saving = true;
        saveError = null;
        saved = false;

        const pointers: PointerOut[] = [...selectedPointers].map(
            (k) => pointerData.get(k)!,
        );
        const relations: RelationOut[] = [...selectedRelations].map(
            (k) => relationData.get(k)!,
        );

        try {
            const res = await fetch(
                `/api/projects/${data.projectId}/curation/${data.referenceId}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ pointers, relations }),
                },
            );
            if (!res.ok) {
                saveError = `Save failed: ${await res.text()}`;
            } else {
                saved = true;
            }
        } catch (e) {
            saveError = String(e);
        } finally {
            saving = false;
        }
    }

    function rowClass(count: number, accepted: boolean): string {
        if (accepted) return "accepted";
        if (snapshots.length === 0) return "";
        if (count === snapshots.length) return "agreement-full";
        if (count >= snapshots.length / 2) return "agreement-partial";
        return "agreement-low";
    }
</script>

<div class="curate-page">
    <div class="curate-header">
        <a href="/curate?project={data.projectId}" class="btn btn-sm">
            ← Back to queue
        </a>
        <div class="reference-meta">
            <h2>{reference.title}</h2>
            <p class="meta-line">
                {reference.authors} · {reference.year}
                {#if reference.pubmed_id}
                    · PMID {reference.pubmed_id}
                {/if}
            </p>
        </div>
    </div>

    {#if snapshots.length === 0}
        <p>No annotator snapshots available for this reference yet.</p>
    {:else}
        <div class="curate-body">
            <div class="curate-tables">
                <div class="annotators-legend">
                    {#each snapshots as snap, i}
                        <span class="annotator-badge annotator-{i % 6}"
                            >{snap.email}</span
                        >
                    {/each}
                </div>

                <!-- ---------------------------------------------------------------- -->
                <!-- Entities table                                                    -->
                <!-- ---------------------------------------------------------------- -->
                <section class="curate-section">
                    <h3>Entities</h3>
                    <p class="section-hint">
                        Overview of all annotated entities. Edit the identifier
                        of proposed entities (marked <span
                            class="proposed-badge">proposed</span
                        >) before saving.
                    </p>
                    <table class="table curate-table">
                        <thead>
                            <tr>
                                <th class="th-accept"></th>
                                <th>Entity</th>
                                <th>Identifier</th>
                                <th>Kind</th>
                                <th>Agreement</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each sortedEntityIds as entityId (entityId)}
                                {@const entity = entities[entityId]}
                                {@const count =
                                    entityAnnotators.get(entityId)!.size}
                                {@const accepted = isEntityAccepted(entityId)}
                                <tr
                                    class={rowClass(
                                        count,
                                        acceptedEntityIds.has(entityId),
                                    )}
                                >
                                    <td class="td-accept">
                                        <button
                                            class="accept-btn {accepted
                                                ? 'accepted'
                                                : ''}"
                                            onclick={() =>
                                                toggleEntity(entityId)}
                                            title={accepted
                                                ? "Remove entity"
                                                : "Accept entity (all its spans)"}
                                        >
                                            {accepted ? "✓" : ""}
                                        </button>
                                    </td>
                                    <td>
                                        <span class="entity-name">
                                            {entity?.preferred_name ?? entityId}
                                        </span>
                                        {#if entity && !entity.confirmed}
                                            <span class="proposed-badge"
                                                >proposed</span
                                            >
                                        {/if}
                                    </td>
                                    <td class="curie-cell">
                                        {#if entity && !entity.confirmed}
                                            <input
                                                class="curie-input"
                                                type="text"
                                                value={curieEdits.get(
                                                    entityId,
                                                ) ?? entityId}
                                                onfocus={() =>
                                                    startCurieEdit(entityId)}
                                                oninput={(e) => {
                                                    curieEdits = new Map(
                                                        curieEdits,
                                                    ).set(
                                                        entityId,
                                                        (
                                                            e.target as HTMLInputElement
                                                        ).value,
                                                    );
                                                }}
                                                onblur={() =>
                                                    applyCurieEdit(entityId)}
                                                onkeydown={(e) => {
                                                    if (e.key === "Enter")
                                                        (
                                                            e.target as HTMLElement
                                                        ).blur();
                                                    if (e.key === "Escape") {
                                                        curieEdits = new Map(
                                                            curieEdits,
                                                        );
                                                        curieEdits.delete(
                                                            entityId,
                                                        );
                                                        (
                                                            e.target as HTMLElement
                                                        ).blur();
                                                    }
                                                }}
                                                disabled={curieSaving.has(
                                                    entityId,
                                                )}
                                                title="Edit CURIE — press Enter to confirm, Escape to cancel"
                                            />
                                            {#if curieErrors.get(entityId)}
                                                <span class="curie-error"
                                                    >{curieErrors.get(
                                                        entityId,
                                                    )}</span
                                                >
                                            {/if}
                                        {:else}
                                            <code class="entity-curie"
                                                >{entityId}</code
                                            >
                                        {/if}
                                    </td>
                                    <td>
                                        <span class="kind-badge"
                                            >{entity?.kind ?? "?"}</span
                                        >
                                    </td>
                                    <td>
                                        <span class="agreement-count"
                                            >{count}/{snapshots.length}</span
                                        >
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </section>

                <!-- ---------------------------------------------------------------- -->
                <!-- Pointers table                                                    -->
                <!-- ---------------------------------------------------------------- -->
                <section class="curate-section">
                    <h3>Pointers</h3>
                    <p class="section-hint">
                        Pre-selected: spans all {snapshots.length} annotator{snapshots.length !==
                        1
                            ? "s"
                            : ""} agree on. Toggle to adjust.
                    </p>
                    <table class="table curate-table">
                        <thead>
                            <tr>
                                <th class="th-accept"></th>
                                <th>Entity</th>
                                <th>Annotated text</th>
                                <th>Agreement</th>
                                <th>Annotators</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each sortedPointerKeys as k (k)}
                                {@const p = pointerData.get(k)!}
                                {@const entity = entities[p.entity_id]}
                                {@const count = pointerAnnotators.get(k)!.size}
                                {@const accepted = selectedPointers.has(k)}
                                <tr
                                    class="pointer-row {rowClass(
                                        count,
                                        acceptedPointerKeys.has(k),
                                    )} {activePointerKey === k
                                        ? 'focused'
                                        : ''}"
                                    onclick={() => focusPointer(k)}
                                >
                                    <td class="td-accept">
                                        <button
                                            class="accept-btn {accepted
                                                ? 'accepted'
                                                : ''}"
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                togglePointer(k);
                                            }}
                                            title={accepted
                                                ? "Remove span"
                                                : "Accept span"}
                                        >
                                            {accepted ? "✓" : ""}
                                        </button>
                                    </td>
                                    <td>
                                        <span class="entity-name">
                                            {entity?.preferred_name ??
                                                p.entity_id}
                                        </span>
                                        <code class="entity-curie"
                                            >{p.entity_id}</code
                                        >
                                    </td>
                                    <td class="span-cell">
                                        {getAnnotatedText(p.offset, p.length) ||
                                            `@${p.offset}+${p.length}`}
                                    </td>
                                    <td>
                                        <span class="agreement-count"
                                            >{count}/{snapshots.length}</span
                                        >
                                    </td>
                                    <td class="annotators-cell">
                                        {[...pointerAnnotators.get(k)!].join(
                                            ", ",
                                        )}
                                    </td>
                                </tr>
                            {/each}
                        </tbody>
                    </table>
                </section>

                <!-- ---------------------------------------------------------------- -->
                <!-- Relations table                                                   -->
                <!-- ---------------------------------------------------------------- -->
                {#if sortedRelationKeys.length > 0}
                    <section class="curate-section">
                        <h3>Relations</h3>
                        <table class="table curate-table">
                            <thead>
                                <tr>
                                    <th class="th-accept"></th>
                                    <th>Subject</th>
                                    <th>Predicate</th>
                                    <th>Object</th>
                                    <th>Agreement</th>
                                </tr>
                            </thead>
                            <tbody>
                                {#each sortedRelationKeys as k (k)}
                                    {@const r = relationData.get(k)!}
                                    {@const count =
                                        relationAnnotators.get(k)!.size}
                                    {@const accepted = selectedRelations.has(k)}
                                    <tr
                                        class={rowClass(
                                            count,
                                            acceptedRelationKeys.has(k),
                                        )}
                                    >
                                        <td class="td-accept">
                                            <button
                                                class="accept-btn {accepted
                                                    ? 'accepted'
                                                    : ''}"
                                                onclick={() =>
                                                    toggleRelation(k)}
                                                title={accepted
                                                    ? "Remove relation"
                                                    : "Accept relation"}
                                            >
                                                {accepted ? "✓" : ""}
                                            </button>
                                        </td>
                                        <td>
                                            <span class="entity-name">
                                                {entities[r.subject]
                                                    ?.preferred_name ??
                                                    r.subject}
                                            </span>
                                            <code class="entity-curie"
                                                >{r.subject}</code
                                            >
                                        </td>
                                        <td><code>{r.predicate}</code></td>
                                        <td>
                                            <span class="entity-name">
                                                {entities[r.object]
                                                    ?.preferred_name ??
                                                    r.object}
                                            </span>
                                            <code class="entity-curie"
                                                >{r.object}</code
                                            >
                                        </td>
                                        <td>
                                            <span class="agreement-count"
                                                >{count}/{snapshots.length}</span
                                            >
                                        </td>
                                    </tr>
                                {/each}
                            </tbody>
                        </table>
                    </section>
                {/if}

                <div class="curate-actions">
                    {#if saveError}
                        <p class="error-msg">{saveError}</p>
                    {/if}
                    {#if saved}
                        <p class="success-msg">Curated annotation saved.</p>
                    {/if}
                    <button
                        class="btn primary"
                        onclick={saveCuration}
                        disabled={saving}
                    >
                        {saving ? "Saving…" : "Save curated annotation"}
                    </button>
                </div>
            </div>
            <!-- end .curate-tables -->

            <!-- ---------------------------------------------------------------- -->
            <!-- Article text panel                                                -->
            <!-- ---------------------------------------------------------------- -->
            <aside class="curate-text-panel">
                <p class="text-panel-title">Article text</p>
                {#if textSegments.length > 0}
                    <div class="article-text">
                        {#each textSegments as seg, i (i)}
                            {#if seg.key !== null}
                                <mark
                                    id="pspan-{seg.idx}"
                                    class="pointer-mark"
                                    class:active={activePointerKey === seg.key}
                                    title={entities[
                                        pointerData.get(seg.key)!.entity_id
                                    ]?.preferred_name ?? seg.key}
                                    onclick={() => focusPointer(seg.key!)}
                                    >{seg.text}</mark
                                >
                            {:else}
                                {seg.text}
                            {/if}
                        {/each}
                    </div>
                {:else}
                    <p class="no-text">No article text available.</p>
                {/if}
            </aside>
        </div>
        <!-- end .curate-body -->
    {/if}
</div>

<style>
    .curate-page {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        padding: 1rem 0;
    }

    .curate-body {
        display: grid;
        grid-template-columns: 1fr 660px;
        gap: 1.5rem;
        align-items: start;
    }

    .curate-tables {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        min-width: 0;
    }

    /* ---- text panel ---- */

    .curate-text-panel {
        position: sticky;
        top: 1rem;
        max-height: calc(100vh - 5rem);
        overflow-y: auto;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        padding: 1rem;
        background: #fafafa;
    }

    .text-panel-title {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
        margin: 0 0 0.75rem;
    }

    .article-text {
        font-size: 1rem;
        line-height: 1.7;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .pointer-mark {
        background: #fef08a;
        border-radius: 2px;
        padding: 0 1px;
        cursor: pointer;
        transition: background 0.1s;
    }

    .pointer-mark:hover {
        background: #fde047;
    }

    .pointer-mark.active {
        background: #f97316;
        color: white;
        border-radius: 3px;
        padding: 1px 3px;
        box-shadow: 0 0 0 2px #f9731660;
    }

    .no-text {
        font-size: 0.8rem;
        color: var(--text-muted, #888);
        margin: 0;
    }

    /* ---- pointer table rows ---- */

    .pointer-row {
        cursor: pointer;
    }

    tr.focused {
        outline: 2px solid var(--primary-color, #4a90e2);
        outline-offset: -2px;
    }

    .curate-header {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .reference-meta h2 {
        margin: 0 0 0.25rem;
        font-size: 1.1rem;
    }

    .meta-line {
        margin: 0;
        color: var(--text-muted, #666);
        font-size: 0.875rem;
    }

    .annotators-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .annotator-badge {
        padding: 0.2rem 0.6rem;
        border-radius: 3px;
        font-size: 0.75rem;
    }

    .annotator-0 {
        background: #dbeafe;
        color: #1e40af;
    }
    .annotator-1 {
        background: #dcfce7;
        color: #166534;
    }
    .annotator-2 {
        background: #fef9c3;
        color: #854d0e;
    }
    .annotator-3 {
        background: #fce7f3;
        color: #9d174d;
    }
    .annotator-4 {
        background: #ede9fe;
        color: #4c1d95;
    }
    .annotator-5 {
        background: #ffedd5;
        color: #7c2d12;
    }

    .curate-section {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .curate-section h3 {
        margin: 0;
        font-size: 1rem;
    }

    .section-hint {
        margin: 0;
        font-size: 0.8rem;
        color: var(--text-muted, #666);
    }

    .curate-table {
        font-size: 0.85rem;
    }

    .entity-name {
        display: block;
        font-weight: 500;
    }

    .entity-curie {
        display: block;
        font-size: 0.75rem;
        color: var(--text-muted, #888);
    }

    .kind-badge {
        font-size: 0.75rem;
        padding: 0.15rem 0.4rem;
        background: var(--bg-subtle, #f3f4f6);
        border-radius: 3px;
    }

    .proposed-badge {
        display: inline-block;
        font-size: 0.7rem;
        padding: 0.1rem 0.35rem;
        background: #fef9c3;
        color: #854d0e;
        border-radius: 3px;
        margin-left: 0.35rem;
        vertical-align: middle;
    }

    .curie-cell {
        min-width: 14rem;
    }

    .curie-input {
        width: 100%;
        font-family: monospace;
        font-size: 0.8rem;
        padding: 0.2rem 0.4rem;
        border: 1px solid #ccc;
        border-radius: 3px;
        box-sizing: border-box;
    }

    .curie-input:focus {
        outline: none;
        border-color: var(--primary-color, #4a90e2);
    }

    .curie-error {
        display: block;
        font-size: 0.7rem;
        color: var(--danger, #dc2626);
        margin-top: 0.15rem;
    }

    .span-cell {
        font-family: monospace;
        font-size: 0.8rem;
    }

    .agreement-count {
        font-size: 0.8rem;
        font-weight: 600;
    }

    .annotators-cell {
        font-size: 0.75rem;
        color: var(--text-muted, #666);
    }

    tr.agreement-full {
        background: #f0fdf4;
    }
    tr.agreement-partial {
        background: #fefce8;
    }
    tr.agreement-low {
        background: #fff7ed;
    }
    tr.accepted {
        background: #dcfce7;
        color: #166534;
    }

    .th-accept {
        width: 2.5rem;
        padding-right: 0;
    }

    .td-accept {
        padding-right: 0;
        vertical-align: middle;
    }

    .accept-btn {
        width: 1.75rem;
        height: 1.75rem;
        border-radius: 50%;
        border: 2px solid #d1d5db;
        background: white;
        cursor: pointer;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        transition:
            border-color 0.12s,
            background 0.12s,
            color 0.12s;
        color: transparent;
    }

    .accept-btn:hover {
        border-color: #16a34a;
        color: #16a34a;
    }

    .accept-btn.accepted {
        border-color: #16a34a;
        background: #16a34a;
        color: white;
    }

    .accept-btn.accepted:hover {
        border-color: #dc2626;
        background: #dc2626;
        color: white;
    }

    .curate-actions {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 0.5rem;
        padding-top: 0.5rem;
    }

    .error-msg {
        color: var(--danger, #dc2626);
        margin: 0;
        font-size: 0.875rem;
    }

    .success-msg {
        color: var(--success, #16a34a);
        margin: 0;
        font-size: 0.875rem;
    }
</style>
