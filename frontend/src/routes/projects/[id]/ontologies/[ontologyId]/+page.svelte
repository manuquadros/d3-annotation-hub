<script lang="ts">
    import { untrack } from "svelte";
    import "$lib/management.css";

    interface Ontology {
        ontology_id: number;
        name: string;
        prefix: string;
        uri: string;
        version: string | null;
    }

    interface Entity {
        entity_id: string; // holds the CURIE
        preferred_name: string;
        kind: string;
    }

    interface Triple {
        subject_curie: string;
        subject_name: string;
        predicate: string;
        object_curie: string | null;
        object_name: string | null;
        object_literal: string | null;
    }

    interface Property {
        curie: string;
        label: string;
        domain_curie: string | null;
        range_curie: string | null;
    }

    let { data } = $props();

    const ontology: Ontology = data.ontology;

    let entities = $state<Entity[]>(untrack(() => data.entities));
    let entitiesTotal = $state<number>(untrack(() => data.entitiesTotal));
    let entitiesOffset = $state(0);
    const PAGE_SIZE = 10;

    let loadingEntities = $state(false);

    let entityCurieFilter = $state("");
    let entityNameFilter = $state("");
    let entityTypeFilter = $state("");

    let entityFilterTimer: ReturnType<typeof setTimeout>;

    async function loadEntitiesPage(offset: number) {
        loadingEntities = true;
        try {
            const qs = new URLSearchParams({
                limit: String(PAGE_SIZE),
                offset: String(offset),
                curie_filter: entityCurieFilter,
                name_filter: entityNameFilter,
                type_filter: entityTypeFilter,
            });
            const res = await fetch(`/api/admin/ontology/${ontology.ontology_id}?${qs}`);
            if (!res.ok) return;
            const d = await res.json();
            entities = d.entities ?? [];
            entitiesTotal = d.total ?? 0;
            entitiesOffset = offset;
        } finally {
            loadingEntities = false;
        }
    }

    {
        let initialEntityRun = true;
        $effect(() => {
            const _c = entityCurieFilter;
            const _n = entityNameFilter;
            const _t = entityTypeFilter;
            if (initialEntityRun) { initialEntityRun = false; return; }
            clearTimeout(entityFilterTimer);
            entityFilterTimer = setTimeout(() => loadEntitiesPage(0), 300);
        });
    }

    let triples = $state<Triple[]>(untrack(() => data.triples));
    let triplesTotal = $state<number>(untrack(() => data.triplesTotal));
    let triplesOffset = $state(0);

    let loadingTriples = $state(false);

    let tripleSubjectFilter = $state("");
    let triplePredicateFilter = $state("");
    let tripleObjectFilter = $state("");

    let tripleFilterTimer: ReturnType<typeof setTimeout>;

    async function loadTriplesPage(offset: number) {
        loadingTriples = true;
        try {
            const qs = new URLSearchParams({
                limit: String(PAGE_SIZE),
                offset: String(offset),
                subject_filter: tripleSubjectFilter,
                predicate_filter: triplePredicateFilter,
                object_filter: tripleObjectFilter,
            });
            const res = await fetch(
                `/api/admin/ontology/${ontology.ontology_id}/triples?${qs}`,
            );
            if (!res.ok) return;
            const d = await res.json();
            triples = d.triples ?? [];
            triplesTotal = d.total ?? 0;
            triplesOffset = offset;
        } finally {
            loadingTriples = false;
        }
    }

    {
        let initialTripleRun = true;
        $effect(() => {
            const _s = tripleSubjectFilter;
            const _p = triplePredicateFilter;
            const _o = tripleObjectFilter;
            if (initialTripleRun) { initialTripleRun = false; return; }
            clearTimeout(tripleFilterTimer);
            tripleFilterTimer = setTimeout(() => loadTriplesPage(0), 300);
        });
    }

    const properties: Property[] = untrack(() => data.properties);

    let propCurieFilter = $state("");
    let propLabelFilter = $state("");
    let propDomainFilter = $state("");
    let propRangeFilter = $state("");

    let filteredProperties = $derived(
        properties.filter(
            (p) =>
                (!propCurieFilter ||
                    p.curie.toLowerCase().includes(propCurieFilter.toLowerCase())) &&
                (!propLabelFilter ||
                    p.label.toLowerCase().includes(propLabelFilter.toLowerCase())) &&
                (!propDomainFilter ||
                    (p.domain_curie ?? "")
                        .toLowerCase()
                        .includes(propDomainFilter.toLowerCase())) &&
                (!propRangeFilter ||
                    (p.range_curie ?? "")
                        .toLowerCase()
                        .includes(propRangeFilter.toLowerCase())),
        ),
    );
</script>

<div class="page">
    <div class="page-header">
        <a href="/projects/{data.projectId}/ontologies" class="back-link">
            <i class="ph ph-arrow-left"></i> Ontologies
        </a>
        <h1>{ontology.name}</h1>
        <div class="meta">
            <code>{ontology.prefix}</code>
            {#if ontology.uri}<span class="uri">{ontology.uri}</span>{/if}
            {#if ontology.version}<span class="version"
                    >v{ontology.version}</span
                >{/if}
        </div>
    </div>

    <section class="card">
        <div class="section-header">
            <h2>Classes</h2>
            <span class="count">{entitiesTotal.toLocaleString()}</span>
        </div>
        {#if entities.length === 0 && !entityCurieFilter && !entityNameFilter && !entityTypeFilter}
            <p class="empty">No classes found.</p>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>CURIE</th>
                        <th>Name</th>
                        <th>Type</th>
                    </tr>
                    <tr class="filter-row">
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={entityCurieFilter}
                            />
                        </th>
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={entityNameFilter}
                            />
                        </th>
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={entityTypeFilter}
                            />
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {#if entities.length === 0}
                        <tr>
                            <td colspan="3" class="empty">No matching classes.</td>
                        </tr>
                    {:else}
                        {#each entities as e (e.entity_id)}
                            <tr>
                                <td><code>{e.entity_id}</code></td>
                                <td>{e.preferred_name}</td>
                                <td><span class="type-badge">{e.kind}</span></td>
                            </tr>
                        {/each}
                    {/if}
                </tbody>
            </table>
            {#if entitiesTotal > PAGE_SIZE}
                <div class="pagination">
                    <button
                        class="btn-secondary"
                        disabled={entitiesOffset === 0 || loadingEntities}
                        onclick={() =>
                            loadEntitiesPage(entitiesOffset - PAGE_SIZE)}
                    >
                        Previous
                    </button>
                    <span class="page-info">
                        {entitiesOffset + 1}–{Math.min(
                            entitiesOffset + PAGE_SIZE,
                            entitiesTotal,
                        )}
                        of {entitiesTotal.toLocaleString()}
                    </span>
                    <button
                        class="btn-secondary"
                        disabled={entitiesOffset + PAGE_SIZE >= entitiesTotal ||
                            loadingEntities}
                        onclick={() =>
                            loadEntitiesPage(entitiesOffset + PAGE_SIZE)}
                    >
                        Next
                    </button>
                </div>
            {/if}
        {/if}
    </section>

    {#if properties.length > 0}
        <section class="card">
            <div class="section-header">
                <h2>Object Properties</h2>
                <span class="count">{filteredProperties.length}</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>CURIE</th>
                        <th>Label</th>
                        <th>Domain</th>
                        <th>Range</th>
                    </tr>
                    <tr class="filter-row">
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={propCurieFilter}
                            />
                        </th>
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={propLabelFilter}
                            />
                        </th>
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={propDomainFilter}
                            />
                        </th>
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={propRangeFilter}
                            />
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {#if filteredProperties.length === 0}
                        <tr>
                            <td colspan="4" class="empty">No matching properties.</td>
                        </tr>
                    {:else}
                        {#each filteredProperties as p (p.curie)}
                            <tr>
                                <td><code>{p.curie}</code></td>
                                <td>{p.label}</td>
                                <td>{p.domain_curie ?? "—"}</td>
                                <td>{p.range_curie ?? "—"}</td>
                            </tr>
                        {/each}
                    {/if}
                </tbody>
            </table>
        </section>
    {/if}

    <section class="card">
        <div class="section-header">
            <h2>Triples</h2>
            <span class="count">{triplesTotal.toLocaleString()}</span>
        </div>
        {#if triples.length === 0 && !tripleSubjectFilter && !triplePredicateFilter && !tripleObjectFilter}
            <p class="empty">No triples found.</p>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>Subject</th>
                        <th>Predicate</th>
                        <th>Object</th>
                    </tr>
                    <tr class="filter-row">
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={tripleSubjectFilter}
                            />
                        </th>
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={triplePredicateFilter}
                            />
                        </th>
                        <th>
                            <input
                                type="search"
                                class="filter-input"
                                placeholder="Filter…"
                                bind:value={tripleObjectFilter}
                            />
                        </th>
                    </tr>
                </thead>
                <tbody>
                    {#if triples.length === 0}
                        <tr>
                            <td colspan="3" class="empty">No matching triples.</td>
                        </tr>
                    {:else}
                        {#each triples as t, i (i)}
                            <tr>
                                <td>
                                    <span class="entity-cell">
                                        <code>{t.subject_curie}</code>
                                        {#if t.subject_name}
                                            <span class="entity-name"
                                                >{t.subject_name}</span
                                            >
                                        {/if}
                                    </span>
                                </td>
                                <td
                                    ><code class="predicate">{t.predicate}</code
                                    ></td
                                >
                                <td>
                                    {#if t.object_literal}
                                        <span class="literal"
                                            >"{t.object_literal}"</span
                                        >
                                    {:else}
                                        <span class="entity-cell">
                                            <code>{t.object_curie ?? "—"}</code>
                                            {#if t.object_name}
                                                <span class="entity-name"
                                                    >{t.object_name}</span
                                                >
                                            {/if}
                                        </span>
                                    {/if}
                                </td>
                            </tr>
                        {/each}
                    {/if}
                </tbody>
            </table>
            {#if triplesTotal > PAGE_SIZE}
                <div class="pagination">
                    <button
                        class="btn-secondary"
                        disabled={triplesOffset === 0 || loadingTriples}
                        onclick={() =>
                            loadTriplesPage(triplesOffset - PAGE_SIZE)}
                    >
                        Previous
                    </button>
                    <span class="page-info">
                        {triplesOffset + 1}–{Math.min(
                            triplesOffset + PAGE_SIZE,
                            triplesTotal,
                        )}
                        of {triplesTotal.toLocaleString()}
                    </span>
                    <button
                        class="btn-secondary"
                        disabled={triplesOffset + PAGE_SIZE >= triplesTotal ||
                            loadingTriples}
                        onclick={() =>
                            loadTriplesPage(triplesOffset + PAGE_SIZE)}
                    >
                        Next
                    </button>
                </div>
            {/if}
        {/if}
    </section>
</div>

<style>
    .page-header {
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
    }

    .back-link {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        font-size: 0.85rem;
        color: #555;
        text-decoration: none;
    }

    .back-link:hover {
        color: #111;
    }

    .meta {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-size: 0.875rem;
        color: #666;
    }

    .uri {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 400px;
    }

    .version {
        background: #f0f0f0;
        border-radius: 3px;
        padding: 0.1rem 0.4rem;
        font-size: 0.8rem;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }

    .count {
        font-size: 0.8rem;
        background: #f0f0f0;
        color: #555;
        border-radius: 10px;
        padding: 0.1rem 0.5rem;
        font-weight: 500;
    }

    .type-badge {
        font-size: 0.78rem;
        background: #e8f0fe;
        color: #3a5bc7;
        border-radius: 3px;
        padding: 0.1rem 0.4rem;
    }

    .entity-cell {
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
    }

    .entity-name {
        font-size: 0.82rem;
        color: #555;
    }

    .predicate {
        font-size: 0.82rem;
        color: #7b5ea7;
    }

    .literal {
        font-style: italic;
        color: #555;
        font-size: 0.88rem;
    }

    .pagination {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding-top: 0.5rem;
        border-top: 1px solid #eee;
    }

    .page-info {
        font-size: 0.85rem;
        color: #666;
    }

    .filter-row th {
        padding: 0.3rem 0.5rem;
        background: #fafafa;
        border-bottom: 1px solid #e8e8e8;
    }

    .filter-input {
        width: 100%;
        box-sizing: border-box;
        padding: 0.25rem 0.4rem;
        font-size: 0.82rem;
        border: 1px solid #ddd;
        border-radius: 3px;
        background: #fff;
        outline: none;
    }

    .filter-input:focus {
        border-color: #aaa;
    }
</style>
