<script lang="ts">
    import type { PageData } from "./$types";
    import type { PointerOut, RelationOut } from "./+page.server";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();

    const { reference, entities, snapshots } = data.data;

    // Build a unified list of unique pointers across all snapshots.
    // Key: "entity_id|offset|length"
    type PointerKey = string;
    function pointerKey(p: PointerOut): PointerKey {
        return `${p.entity_id}|${p.offset}|${p.length}`;
    }

    // Map from pointerKey -> set of annotator emails who tagged it
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

    // Sort: pointers tagged by more annotators first, then by entity name
    const sortedPointerKeys = [...pointerAnnotators.keys()].sort((a, b) => {
        const countDiff =
            pointerAnnotators.get(b)!.size - pointerAnnotators.get(a)!.size;
        if (countDiff !== 0) return countDiff;
        const nameA = entities[pointerData.get(a)!.entity_id]?.preferred_name ?? a;
        const nameB = entities[pointerData.get(b)!.entity_id]?.preferred_name ?? b;
        return nameA.localeCompare(nameB);
    });

    // Build unique relations similarly
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

    const sortedRelationKeys = [...relationAnnotators.keys()].sort((a, b) => {
        return (
            relationAnnotators.get(b)!.size - relationAnnotators.get(a)!.size
        );
    });

    // Selection state: which pointers/relations to include in curated output
    let selectedPointers = $state<Set<PointerKey>>(
        // Pre-select pointers that all annotators agree on
        new Set(
            sortedPointerKeys.filter(
                (k) =>
                    pointerAnnotators.get(k)!.size === snapshots.length &&
                    snapshots.length > 0,
            ),
        ),
    );
    let selectedRelations = $state<Set<RelationKey>>(
        new Set(
            sortedRelationKeys.filter(
                (k) =>
                    relationAnnotators.get(k)!.size === snapshots.length &&
                    snapshots.length > 0,
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
                const text = await res.text();
                saveError = `Save failed: ${text}`;
            } else {
                saved = true;
            }
        } catch (e) {
            saveError = String(e);
        } finally {
            saving = false;
        }
    }

    function agreementClass(count: number): string {
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
        <div class="annotators-legend">
            {#each snapshots as snap, i}
                <span class="annotator-badge annotator-{i % 6}">{snap.email}</span>
            {/each}
        </div>

        <section class="curate-section">
            <h3>Entities / Pointers</h3>
            <p class="section-hint">
                Pre-selected: pointers all {snapshots.length} annotator{snapshots.length !== 1 ? "s" : ""} agree on.
                Toggle to adjust.
            </p>
            <table class="table curate-table">
                <thead>
                    <tr>
                        <th>Include</th>
                        <th>Entity</th>
                        <th>Kind</th>
                        <th>Span (offset·length)</th>
                        <th>Agreement</th>
                        <th>Annotators</th>
                    </tr>
                </thead>
                <tbody>
                    {#each sortedPointerKeys as k (k)}
                        {@const p = pointerData.get(k)!}
                        {@const entity = entities[p.entity_id]}
                        {@const count = pointerAnnotators.get(k)!.size}
                        <tr class={agreementClass(count)}>
                            <td>
                                <input
                                    type="checkbox"
                                    checked={selectedPointers.has(k)}
                                    onchange={() => togglePointer(k)}
                                />
                            </td>
                            <td>
                                <span class="entity-name">
                                    {entity?.preferred_name ?? p.entity_id}
                                </span>
                                <span class="entity-curie">{p.entity_id}</span>
                            </td>
                            <td>
                                <span class="kind-badge">{entity?.kind ?? "?"}</span>
                            </td>
                            <td class="span-cell">{p.offset}·{p.length}</td>
                            <td>
                                <span class="agreement-count"
                                    >{count}/{snapshots.length}</span
                                >
                            </td>
                            <td class="annotators-cell">
                                {[...pointerAnnotators.get(k)!].join(", ")}
                            </td>
                        </tr>
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
                            <th>Include</th>
                            <th>Subject</th>
                            <th>Predicate</th>
                            <th>Object</th>
                            <th>Agreement</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each sortedRelationKeys as k (k)}
                            {@const r = relationData.get(k)!}
                            {@const count = relationAnnotators.get(k)!.size}
                            <tr class={agreementClass(count)}>
                                <td>
                                    <input
                                        type="checkbox"
                                        checked={selectedRelations.has(k)}
                                        onchange={() => toggleRelation(k)}
                                    />
                                </td>
                                <td>
                                    <span class="entity-name">
                                        {entities[r.subject]?.preferred_name ?? r.subject}
                                    </span>
                                    <span class="entity-curie">{r.subject}</span>
                                </td>
                                <td><code>{r.predicate}</code></td>
                                <td>
                                    <span class="entity-name">
                                        {entities[r.object]?.preferred_name ?? r.object}
                                    </span>
                                    <span class="entity-curie">{r.object}</span>
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
    {/if}
</div>

<style>
    .curate-page {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        padding: 1rem 0;
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
        font-size: 0.8rem;
    }

    .annotator-badge {
        padding: 0.2rem 0.6rem;
        border-radius: 3px;
        font-size: 0.75rem;
    }

    /* Cycle through some muted background colours */
    .annotator-0 { background: #dbeafe; color: #1e40af; }
    .annotator-1 { background: #dcfce7; color: #166534; }
    .annotator-2 { background: #fef9c3; color: #854d0e; }
    .annotator-3 { background: #fce7f3; color: #9d174d; }
    .annotator-4 { background: #ede9fe; color: #4c1d95; }
    .annotator-5 { background: #ffedd5; color: #7c2d12; }

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
        font-family: monospace;
    }

    .kind-badge {
        font-size: 0.75rem;
        padding: 0.15rem 0.4rem;
        background: var(--bg-subtle, #f3f4f6);
        border-radius: 3px;
    }

    .span-cell {
        font-family: monospace;
        font-size: 0.8rem;
        white-space: nowrap;
    }

    .agreement-count {
        font-size: 0.8rem;
        font-weight: 600;
    }

    .annotators-cell {
        font-size: 0.75rem;
        color: var(--text-muted, #666);
    }

    /* Row colouring by agreement level */
    tr.agreement-full {
        background: #f0fdf4;
    }

    tr.agreement-partial {
        background: #fefce8;
    }

    tr.agreement-low {
        background: #fff7ed;
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
