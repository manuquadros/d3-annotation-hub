<script lang="ts">
    import { invalidateAll, goto } from "$app/navigation";
    import { browser } from "$app/environment";
    import { untrack } from "svelte";
    import type { PageData } from "./$types";
    import type { PointerOut, RelationOut } from "./+page.server";
    import {
        computeReviewModel,
        type PointerKey,
        type RelationKey,
        type SpanEntry,
    } from "$lib/utils/curationReview";
    import {
        resolvePointerOffset,
        createRangeFromOffsets,
    } from "$lib/annotation.svelte";
    import DOMPurify from "dompurify";
    import type { Pointer } from "$lib/types.ts";
    import { errorDetail } from "$lib/utils/http";
    import { SaveSequencer } from "$lib/utils/saveSequencer";
    import CurieEditor from "$lib/components/CurieEditor.svelte";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();

    // Everything below is a pure function of the loaded page data, so it is
    // derived (not seeded once) — a CURIE rename re-fetches via invalidateAll()
    // and the whole view, including the save payload, tracks the new data.
    const reference = $derived(data.data.reference);
    const snapshots = $derived(data.data.snapshots);
    const entities = $derived(data.data.entities);

    const model = $derived.by(() => computeReviewModel(data.data));
    const pointerAnnotators = $derived(model.pointerAnnotators);
    const pointerData = $derived(model.pointerData);
    const entityAnnotators = $derived(model.entityAnnotators);
    const relationAnnotators = $derived(model.relationAnnotators);
    const relationData = $derived(model.relationData);
    const abstractSpansByOffset = $derived(model.abstractSpansByOffset);
    const bodySpansByOffset = $derived(model.bodySpansByOffset);
    const spanIndexByKey = $derived(model.spanIndexByKey);
    const acceptedPointerKeys = $derived(model.acceptedPointerKeys);
    const acceptedRelationKeys = $derived(model.acceptedRelationKeys);
    const acceptedEntityIds = $derived(model.acceptedEntityIds);
    const sortedPointerKeys = $derived(model.sortedPointerKeys);
    const pointerKeysByEntity = $derived(model.pointerKeysByEntity);
    const sortedEntityIds = $derived(model.sortedEntityIds);
    const sortedRelationKeys = $derived(model.sortedRelationKeys);
    const hasSavedCuration = $derived(model.hasSavedCuration);

    function toPlainText(html: string | null): string {
        if (!browser || !html) return "";
        return (
            new DOMParser().parseFromString(html, "text/html").body
                .textContent ?? ""
        );
    }

    const abstractPlainText = $derived(toPlainText(reference.abstract));
    const bodyPlainText = $derived(toPlainText(reference.body));

    function getAnnotatedText(p: PointerOut): string {
        if (p.exact_text) return p.exact_text;
        const pt = p.field === "abstract" ? abstractPlainText : bodyPlainText;
        return pt.slice(p.offset, p.offset + p.length);
    }

    function renderField(
        element: HTMLDivElement,
        html: string | null,
        spans: SpanEntry[],
    ) {
        if (!html) {
            element.replaceChildren();
            return;
        }
        element.innerHTML = DOMPurify.sanitize(html);
        const pt = element.textContent || "";

        for (const { key, p } of spans) {
            const resolved = resolvePointerOffset(p as unknown as Pointer, pt);
            if (!resolved) continue;
            const range = createRangeFromOffsets(
                element,
                resolved.offset,
                resolved.offset + resolved.length,
            );
            if (!range) continue;

            const idx = spanIndexByKey.get(key)!;
            const mark = document.createElement("mark");
            mark.id = `pspan-${idx}`;
            mark.className = "pointer-mark";
            mark.dataset.pointerKey = key;
            mark.title = entities[p.entity_id]?.preferred_name ?? key;
            mark.addEventListener("click", () => focusPointer(key));

            mark.appendChild(range.extractContents());
            range.insertNode(mark);
        }
    }

    let activePointerKey = $state<PointerKey | null>(null);
    let activeEntityId = $state<string | null>(null);

    function getMentionContext(
        p: PointerOut,
        window = 60,
    ): { before: string; match: string; after: string } {
        const pt = p.field === "abstract" ? abstractPlainText : bodyPlainText;
        const start = p.offset;
        const end = p.offset + p.length;
        const beforeStart = Math.max(0, start - window);
        const afterEnd = Math.min(pt.length, end + window);
        return {
            before: (beforeStart > 0 ? "…" : "") + pt.slice(beforeStart, start),
            match: pt.slice(start, end) || p.exact_text || "",
            after: pt.slice(end, afterEnd) + (afterEnd < pt.length ? "…" : ""),
        };
    }

    function focusPointer(k: PointerKey) {
        activePointerKey = k;
        const p = pointerData.get(k);
        if (p) activeEntityId = p.entity_id;
        const idx = spanIndexByKey.get(k);
        if (idx !== undefined) {
            document
                .getElementById(`pspan-${idx}`)
                ?.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        // Double rAF: wait for entity expansion to render before scrolling mention into view
        requestAnimationFrame(() =>
            requestAnimationFrame(() => {
                document
                    .querySelector(`[data-mention-key="${CSS.escape(k)}"]`)
                    ?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }),
        );
    }

    $effect(() => {
        function onKeydown(e: KeyboardEvent) {
            const tag = (e.target as HTMLElement).tagName;
            if (tag === "INPUT" || tag === "BUTTON" || tag === "TEXTAREA")
                return;

            if (e.key === " " && activePointerKey !== null) {
                e.preventDefault();
                setMentionAccepted(
                    activePointerKey,
                    !selectedPointers.has(activePointerKey),
                );
                return;
            }

            const isNext = e.key === "ArrowDown" || e.key === "j";
            const isPrev = e.key === "ArrowUp" || e.key === "k";
            if (!isNext && !isPrev) return;
            e.preventDefault();

            const keys = sortedPointerKeys;
            if (keys.length === 0) return;

            let idx =
                activePointerKey === null
                    ? isNext
                        ? -1
                        : 0
                    : keys.indexOf(activePointerKey);

            idx = isNext
                ? Math.min(idx + 1, keys.length - 1)
                : Math.max(idx - 1, 0);

            focusPointer(keys[idx]);
        }
        document.addEventListener("keydown", onKeydown);
        return () => document.removeEventListener("keydown", onKeydown);
    });

    $effect(() => {
        const active = activePointerKey;
        document
            .querySelectorAll(".curate-text-panel .pointer-mark.active")
            .forEach((el) => el.classList.remove("active"));
        if (active !== null) {
            const idx = spanIndexByKey.get(active);
            if (idx !== undefined) {
                document
                    .getElementById(`pspan-${idx}`)
                    ?.classList.add("active");
            }
        }
    });

    interface MentionGroup {
        displayText: string;
        keys: PointerKey[];
    }

    const mentionGroupsByEntity = $derived(
        (() => {
            const result = new Map<string, MentionGroup[]>();
            for (const [entityId, keys] of pointerKeysByEntity) {
                const groups = new Map<string, MentionGroup>();
                for (const k of keys) {
                    const p = pointerData.get(k)!;
                    const text =
                        getAnnotatedText(p) ||
                        `@${p.field}:${p.offset}+${p.length}`;
                    const caseKey = text.toLowerCase();
                    if (!groups.has(caseKey)) {
                        groups.set(caseKey, { displayText: text, keys: [] });
                    }
                    groups.get(caseKey)!.keys.push(k);
                }
                result.set(entityId, [...groups.values()]);
            }
            return result;
        })(),
    );

    const pointerGroupKeys = $derived(
        (() => {
            const map = new Map<PointerKey, string>();
            for (const [entityId, groups] of mentionGroupsByEntity) {
                for (const group of groups) {
                    const gk = `${entityId}|${group.displayText.toLowerCase()}`;
                    for (const k of group.keys) map.set(k, gk);
                }
            }
            return map;
        })(),
    );

    let entityStatus = $state(new Map<string, boolean>());
    let groupStatus = $state(new Map<string, boolean>());
    // Seed once from the initial derivation; user toggles persist across a
    // later re-derivation (a renamed entity's keys change and re-default to
    // accepted, which is the intended behaviour).
    let mentionOverrides = $state<Map<PointerKey, boolean>>(
        untrack(() => {
            const initial = new Map<PointerKey, boolean>();
            if (hasSavedCuration) {
                for (const k of sortedPointerKeys) {
                    if (!acceptedPointerKeys.has(k)) initial.set(k, false);
                }
            }
            return initial;
        }),
    );

    const selectedPointers = $derived(
        (() => {
            const set = new Set<PointerKey>();
            for (const k of sortedPointerKeys) {
                const gk = pointerGroupKeys.get(k);
                const eid = pointerData.get(k)!.entity_id;
                if (
                    entityStatus.get(eid) !== false &&
                    groupStatus.get(gk ?? "") !== false &&
                    mentionOverrides.get(k) !== false
                ) {
                    set.add(k);
                }
            }
            return set;
        })(),
    );

    let selectedRelations = $state<Set<RelationKey>>(
        untrack(
            () =>
                new Set(
                    hasSavedCuration
                        ? sortedRelationKeys.filter((k) =>
                              acceptedRelationKeys.has(k),
                          )
                        : sortedRelationKeys.filter(
                              (k) =>
                                  relationAnnotators.get(k)!.size ===
                                      snapshots.length && snapshots.length > 0,
                          ),
                ),
        ),
    );

    function setMentionAccepted(k: PointerKey, accepted: boolean) {
        const next = new Map(mentionOverrides);
        if (accepted) next.delete(k);
        else next.set(k, false);
        mentionOverrides = next;
    }

    function toggleRelation(k: RelationKey) {
        const next = new Set(selectedRelations);
        if (next.has(k)) next.delete(k);
        else next.add(k);
        selectedRelations = next;
    }

    function isEntityAccepted(entityId: string): boolean {
        const keys = pointerKeysByEntity.get(entityId) ?? [];
        return keys.some((k) => selectedPointers.has(k));
    }

    function toggleEntity(entityId: string) {
        const next = new Map(entityStatus);
        if (isEntityAccepted(entityId)) next.set(entityId, false);
        else next.delete(entityId);
        entityStatus = next;
    }

    function setGroupAccepted(
        entityId: string,
        displayText: string,
        accepted: boolean,
    ) {
        const gk = `${entityId}|${displayText.toLowerCase()}`;
        const next = new Map(groupStatus);
        if (accepted) next.delete(gk);
        else next.set(gk, false);
        groupStatus = next;
    }

    let locallyConfirmed = $state(new Set<string>());

    // Rename a proposed entity's CURIE, or — when unchanged — confirm it as-is.
    // Throws on a failed rename so CurieEditor surfaces the message inline and
    // keeps the editor open.
    async function saveCurie(entityId: string, newCurie: string) {
        if (newCurie !== entityId) {
            const res = await fetch(
                `/api/projects/${data.projectId}/curation/entity-curie?curie=${encodeURIComponent(entityId)}`,
                {
                    method: "PATCH",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ new_curie: newCurie }),
                },
            );
            if (!res.ok) throw new Error(await errorDetail(res));
        }
        // After invalidateAll() the entity re-derives under its new CURIE, so
        // record the confirmation against the new key.
        const confirmed = new Set(locallyConfirmed);
        confirmed.delete(entityId);
        confirmed.add(newCurie);
        locallyConfirmed = confirmed;
        if (newCurie !== entityId) await invalidateAll();
    }

    let autosaving = $state(false);
    let autosaveError = $state<string | null>(null);
    let autosaved = $state(false);

    function buildCurationPayload() {
        const pointers: PointerOut[] = [...selectedPointers].map(
            (k) => pointerData.get(k)!,
        );
        const relations: RelationOut[] = [...selectedRelations].map(
            (k) => relationData.get(k)!,
        );
        return { pointers, relations };
    }

    // A curation POST replaces the whole curated annotation, so an older
    // in-flight save landing after a newer one would overwrite it with stale
    // data. The sequencer aborts the prior request and lets us ignore any
    // superseded result.
    const saveSequencer = new SaveSequencer();

    async function save() {
        const { signal, isCurrent } = saveSequencer.begin();

        autosaving = true;
        autosaveError = null;
        try {
            const res = await fetch(
                `/api/projects/${data.projectId}/curation/${data.referenceId}`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(buildCurationPayload()),
                    signal,
                },
            );
            if (!isCurrent()) return;
            if (!res.ok) {
                autosaveError = await errorDetail(res);
            } else {
                autosaved = true;
            }
        } catch (e) {
            if (signal.aborted || !isCurrent()) return;
            autosaveError = String(e);
        } finally {
            if (isCurrent()) autosaving = false;
        }
    }

    let autosaveInitialized = false;
    $effect(() => {
        const _ = [selectedPointers, selectedRelations];
        if (!autosaveInitialized) {
            autosaveInitialized = true;
            return;
        }
        autosaved = false;
        const timer = setTimeout(save, 1500);
        return () => clearTimeout(timer);
    });

    function completionBlockers(): string[] {
        const msgs: string[] = [];
        if (
            sortedEntityIds.some(
                (id) =>
                    entities[id] &&
                    !entities[id].confirmed &&
                    !locallyConfirmed.has(id),
            )
        ) {
            msgs.push(
                "Proposed entities have not been assigned a confirmed identifier.",
            );
        }
        if (
            snapshots.length > 1 &&
            sortedPointerKeys.some(
                (k) =>
                    selectedPointers.has(k) &&
                    pointerAnnotators.get(k)!.size < snapshots.length,
            )
        ) {
            msgs.push(
                "Some accepted mentions have annotator disagreements that have not been reviewed.",
            );
        }
        return msgs;
    }

    async function markAsComplete() {
        const blockers = completionBlockers();
        if (blockers.length > 0) {
            const msg =
                "Please resolve the following before marking as complete:\n\n" +
                blockers.map((b) => "• " + b).join("\n") +
                "\n\nProceed anyway?";
            if (!confirm(msg)) return;
        }
        await save();
        if (!autosaveError) {
            goto(`/curate?project=${data.projectId}`);
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
        <a href="/curate?project={data.projectId}" class="btn small">
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
                    {#each snapshots as snap, i (snap.user_id)}
                        <span class="annotator-badge annotator-{i % 6}"
                            >{snap.email}</span
                        >
                    {/each}
                </div>

                <section class="curate-section">
                    <h3>Entities</h3>
                    <p class="section-hint">
                        Click an entity to see its mentions. Mentions are
                        accepted by default — remove or reassign them as needed.
                        Edit the identifier of proposed entities (marked <span
                            class="proposed-badge">proposed</span
                        >) before saving.
                    </p>
                    <table class="table curate-table">
                        <thead>
                            <tr>
                                <th class="th-accept"></th>
                                <th>Entity</th>
                                <th>Identifier</th>
                                <th>Class</th>
                                <th>Agreement</th>
                            </tr>
                        </thead>
                        <tbody>
                            {#each sortedEntityIds as entityId (entityId)}
                                {@const entity = entities[entityId]}
                                {@const count =
                                    entityAnnotators.get(entityId)!.size}
                                {@const accepted = isEntityAccepted(entityId)}
                                {@const isExpanded =
                                    activeEntityId === entityId}
                                <tr
                                    class="entity-row {rowClass(
                                        count,
                                        acceptedEntityIds.has(entityId),
                                    )} {isExpanded ? 'expanded' : ''}"
                                    onclick={() => {
                                        activeEntityId = isExpanded
                                            ? null
                                            : entityId;
                                    }}
                                >
                                    <td class="td-accept">
                                        <button
                                            class="accept-btn {accepted
                                                ? 'accepted'
                                                : ''}"
                                            onclick={(e) => {
                                                e.stopPropagation();
                                                toggleEntity(entityId);
                                            }}
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
                                    <td
                                        class="curie-cell"
                                        onclick={(e) => e.stopPropagation()}
                                    >
                                        {#if entity && !entity.confirmed}
                                            <div class="curie-with-status">
                                                <CurieEditor
                                                    curie={entityId}
                                                    confirmUnchanged
                                                    save={(newCurie) =>
                                                        saveCurie(
                                                            entityId,
                                                            newCurie,
                                                        )}
                                                />
                                                {#if locallyConfirmed.has(entityId)}
                                                    <span
                                                        class="curie-status confirmed"
                                                        title="Identifier confirmed"
                                                        >✓</span
                                                    >
                                                {:else}
                                                    <span
                                                        class="curie-status unconfirmed"
                                                        title="Identifier not yet confirmed — click the CURIE to edit"
                                                        >?</span
                                                    >
                                                {/if}
                                            </div>
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
                                    <td class="agreement-expand-cell">
                                        <span class="agreement-count"
                                            >{count}/{snapshots.length}</span
                                        >
                                        <span class="expand-chevron"
                                            >{isExpanded ? "▲" : "▼"}</span
                                        >
                                    </td>
                                </tr>
                                {#if isExpanded}
                                    <tr class="mention-expansion-row">
                                        <td
                                            colspan="5"
                                            class="mention-expansion-cell"
                                        >
                                            <ul class="mention-list">
                                                {#each mentionGroupsByEntity.get(entityId) ?? [] as group (group.displayText)}
                                                    {@const gAccepted =
                                                        group.keys.some((k) =>
                                                            selectedPointers.has(
                                                                k,
                                                            ),
                                                        )}
                                                    <li class="mention-group">
                                                        <div
                                                            class="mention-group-header"
                                                        >
                                                            <button
                                                                class="accept-btn {gAccepted
                                                                    ? 'accepted'
                                                                    : ''}"
                                                                onclick={() =>
                                                                    setGroupAccepted(
                                                                        entityId,
                                                                        group.displayText,
                                                                        !gAccepted,
                                                                    )}
                                                                title={gAccepted
                                                                    ? "Reject all occurrences"
                                                                    : "Accept all occurrences"}
                                                                >✓</button
                                                            >
                                                            <span
                                                                class="mention-group-text"
                                                                >{group.displayText}</span
                                                            >
                                                        </div>
                                                        <ul
                                                            class="mention-sublist"
                                                        >
                                                            {#each group.keys as k (k)}
                                                                {@const p =
                                                                    pointerData.get(
                                                                        k,
                                                                    )!}
                                                                {@const pAccepted =
                                                                    selectedPointers.has(
                                                                        k,
                                                                    )}
                                                                {@const pCount =
                                                                    pointerAnnotators.get(
                                                                        k,
                                                                    )!.size}
                                                                {@const ctx =
                                                                    getMentionContext(
                                                                        p,
                                                                    )}
                                                                <li
                                                                    class="mention-item {activePointerKey ===
                                                                    k
                                                                        ? 'active'
                                                                        : ''} {!pAccepted
                                                                        ? 'removed'
                                                                        : ''}"
                                                                    data-mention-key={k}
                                                                >
                                                                    <button
                                                                        class="mention-focus-btn"
                                                                        onclick={() =>
                                                                            focusPointer(
                                                                                k,
                                                                            )}
                                                                    >
                                                                        <span
                                                                            class="mention-field-badge"
                                                                            >{p.field}</span
                                                                        >
                                                                        <span
                                                                            class="mention-kwic-group"
                                                                            ><span
                                                                                class="mention-kwic"
                                                                                ><span
                                                                                    class="kwic-context"
                                                                                    >{ctx.before}</span
                                                                                ><mark
                                                                                    class="kwic-match"
                                                                                    >{ctx.match}</mark
                                                                                ><span
                                                                                    class="kwic-context"
                                                                                    >{ctx.after}</span
                                                                                ></span
                                                                            ></span
                                                                        >
                                                                        <span
                                                                            class="mention-agreement"
                                                                            >{pCount}/{snapshots.length}</span
                                                                        >
                                                                    </button>
                                                                    <button
                                                                        class="mention-toggle-btn {pAccepted
                                                                            ? 'reject'
                                                                            : 'accept'}"
                                                                        onclick={() =>
                                                                            setMentionAccepted(
                                                                                k,
                                                                                !pAccepted,
                                                                            )}
                                                                        title={pAccepted
                                                                            ? "Reject this mention"
                                                                            : "Accept this mention"}
                                                                        >{pAccepted
                                                                            ? "×"
                                                                            : "✓"}</button
                                                                    >
                                                                </li>
                                                            {/each}
                                                        </ul>
                                                    </li>
                                                {/each}
                                            </ul>
                                        </td>
                                    </tr>
                                {/if}
                            {/each}
                        </tbody>
                    </table>
                </section>

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
                    <button
                        class="btn primary"
                        onclick={markAsComplete}
                        disabled={autosaving}
                    >
                        Mark as complete
                    </button>

                    <div class="autosave-status">
                        {#if autosaving}
                            <span class="autosave-msg saving">Saving…</span>
                        {:else if autosaveError}
                            <span class="autosave-msg error"
                                >Autosave failed: {autosaveError}</span
                            >
                        {:else if autosaved}
                            <span class="autosave-msg saved">Saved</span>
                        {/if}
                    </div>
                </div>
            </div>

            <aside class="curate-text-panel">
                {#if reference.abstract}
                    <p class="text-panel-title">Abstract</p>
                    <div
                        class="article-text"
                        {@attach (el) =>
                            renderField(
                                el,
                                reference.abstract,
                                abstractSpansByOffset,
                            )}
                    ></div>
                {/if}

                {#if reference.body}
                    <p class="text-panel-title">Full text</p>
                    <div
                        class="article-text"
                        {@attach (el) =>
                            renderField(el, reference.body, bodySpansByOffset)}
                    ></div>
                {/if}

                {#if !reference.abstract && !reference.body}
                    <p class="no-text">No article text available.</p>
                {/if}
            </aside>
        </div>
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
        font-size: 0.9rem;
        line-height: 1.65;
        word-break: break-word;
    }

    .article-text :global(h1),
    .article-text :global(h2),
    .article-text :global(h3),
    .article-text :global(h4) {
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #374151;
        margin: 1rem 0 0.25rem;
    }

    .article-text :global(p) {
        margin: 0 0 0.5rem;
    }

    :global(.pointer-mark) {
        background: #fef08a;
        border-radius: 2px;
        padding: 0 1px;
        cursor: pointer;
        transition: background 0.1s;
    }

    :global(.pointer-mark:hover) {
        background: #fde047;
    }

    :global(.pointer-mark.active) {
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

    .curate-header {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
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

    .curie-with-status {
        display: flex;
        align-items: center;
        gap: 0.3rem;
    }

    .curie-status {
        flex-shrink: 0;
        width: 1.1rem;
        height: 1.1rem;
        border-radius: 50%;
        font-size: 0.65rem;
        font-weight: 700;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
    }

    .curie-status.unconfirmed {
        border: 1px solid #f59e0b;
        color: #b45309;
        background: transparent;
    }

    .curie-status.confirmed {
        border: 1px solid #16a34a;
        color: #16a34a;
        background: #f0fdf4;
    }

    .curie-cell {
        min-width: 14rem;
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
        flex-direction: row;
        align-items: center;
        gap: 1rem;
        padding-top: 0.5rem;
    }

    .autosave-status {
        font-size: 0.8rem;
        min-width: 6rem;
    }

    .autosave-msg.saving {
        color: var(--text-muted, #6b7280);
    }

    .autosave-msg.saved {
        color: var(--success, #16a34a);
    }

    .autosave-msg.error {
        color: var(--danger, #dc2626);
    }

    .entity-row {
        cursor: pointer;
        user-select: none;
    }

    .entity-row.expanded td:first-child {
        box-shadow: inset 3px 0 0 var(--primary-color, #4a90e2);
    }

    .agreement-expand-cell {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        white-space: nowrap;
    }

    .expand-chevron {
        font-size: 0.65rem;
        color: var(--text-muted, #888);
    }

    .mention-expansion-row td {
        padding: 0;
        border-top: none;
    }

    .mention-expansion-cell {
        padding: 0 0 0.5rem 2.5rem !important;
        background: var(--bg-subtle, #f3f4f6);
    }

    .mention-list {
        list-style: none;
        margin: 0;
        padding: 0.25rem 0;
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
    }

    .mention-group {
        list-style: none;
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
    }

    .mention-group-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.5rem;
        cursor: default;
    }

    .mention-focus-btn {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: none;
        border: none;
        padding: 0;
        text-align: left;
        cursor: pointer;
        min-width: 0;
        color: inherit;
    }

    .mention-toggle-btn {
        flex-shrink: 0;
        width: 1.3rem;
        height: 1.3rem;
        border-radius: 50%;
        border: 1px solid currentColor;
        background: transparent;
        cursor: pointer;
        font-size: 0.7rem;
        line-height: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        transition: background 0.1s;
    }

    .mention-toggle-btn.reject {
        color: #dc2626;
        border-color: #fca5a5;
    }

    .mention-toggle-btn.reject:hover {
        background: #fee2e2;
    }

    .mention-toggle-btn.accept {
        color: #16a34a;
        border-color: #86efac;
    }

    .mention-toggle-btn.accept:hover {
        background: #dcfce7;
    }

    .mention-group-text {
        font-family: monospace;
        font-size: 0.83rem;
        font-weight: 600;
        flex: 1;
        min-width: 0;
        word-break: break-word;
    }

    .mention-sublist {
        list-style: none;
        margin: 0;
        padding: 0 0 0 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.15rem;
    }

    .mention-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        border-left: 3px solid transparent;
        cursor: pointer;
        transition: background 0.1s;
    }

    .mention-item:hover {
        background: #e5e7eb;
    }

    .mention-item.active {
        border-left-color: #f97316;
        background: #fff7ed;
    }

    .mention-item.removed {
        opacity: 0.5;
        text-decoration: line-through;
    }

    .mention-kwic-group {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 1em;
        min-width: 0;
        overflow: hidden;
    }

    .mention-kwic {
        flex-shrink: 1;
        min-width: 0;
        font-family: monospace;
        font-size: 0.8rem;
        white-space: nowrap;
        overflow: hidden;
    }

    .kwic-context {
        color: var(--text-muted, #6b7280);
    }

    .kwic-match {
        background: #fef08a;
        border-radius: 2px;
        padding: 0 1px;
        font-weight: 600;
    }

    .mention-item.active .kwic-match {
        background: #f97316;
        color: white;
    }

    .mention-item.removed .kwic-match {
        background: none;
    }

    .mention-field-badge {
        font-size: 0.7rem;
        padding: 0.1rem 0.3rem;
        background: #e5e7eb;
        border-radius: 3px;
        color: #374151;
    }

    .mention-agreement {
        font-size: 0.75rem;
        color: var(--text-muted, #888);
        margin-left: auto;
    }
</style>
