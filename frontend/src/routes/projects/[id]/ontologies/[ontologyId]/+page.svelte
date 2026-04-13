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

    // ── Classes (entities) ───────────────────────────────────────────────────
    let entities = $state<Entity[]>(untrack(() => data.entities));
    let entitiesTotal = $state<number>(untrack(() => data.entitiesTotal));
    let entitiesOffset = $state(0);
    const PAGE_SIZE = 10;

    let loadingEntities = $state(false);

    async function loadEntitiesPage(offset: number) {
        loadingEntities = true;
        try {
            const res = await fetch(
                `/api/admin/ontology/${ontology.ontology_id}?limit=${PAGE_SIZE}&offset=${offset}`,
            );
            if (!res.ok) return;
            const d = await res.json();
            entities = d.entities ?? [];
            entitiesOffset = offset;
        } finally {
            loadingEntities = false;
        }
    }

    // ── Triples ──────────────────────────────────────────────────────────────
    let triples = $state<Triple[]>(untrack(() => data.triples));
    let triplesTotal = $state<number>(untrack(() => data.triplesTotal));
    let triplesOffset = $state(0);

    let loadingTriples = $state(false);

    async function loadTriplesPage(offset: number) {
        loadingTriples = true;
        try {
            const res = await fetch(
                `/api/admin/ontology/${ontology.ontology_id}/triples?limit=${PAGE_SIZE}&offset=${offset}`,
            );
            if (!res.ok) return;
            const d = await res.json();
            triples = d.triples ?? [];
            triplesOffset = offset;
        } finally {
            loadingTriples = false;
        }
    }

    // ── Properties ───────────────────────────────────────────────────────────
    const properties: Property[] = untrack(() => data.properties);
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

    <!-- Classes -->
    <section class="card">
        <div class="section-header">
            <h2>Classes</h2>
            <span class="count">{entitiesTotal.toLocaleString()}</span>
        </div>
        {#if entities.length === 0}
            <p class="empty">No classes found.</p>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>CURIE</th>
                        <th>Name</th>
                        <th>Type</th>
                    </tr>
                </thead>
                <tbody>
                    {#each entities as e (e.entity_id)}
                        <tr>
                            <td><code>{e.entity_id}</code></td>
                            <td>{e.preferred_name}</td>
                            <td><span class="type-badge">{e.kind}</span></td>
                        </tr>
                    {/each}
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

    <!-- Properties -->
    {#if properties.length > 0}
        <section class="card">
            <div class="section-header">
                <h2>Object Properties</h2>
                <span class="count">{properties.length}</span>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>CURIE</th>
                        <th>Label</th>
                        <th>Domain</th>
                        <th>Range</th>
                    </tr>
                </thead>
                <tbody>
                    {#each properties as p (p.curie)}
                        <tr>
                            <td><code>{p.curie}</code></td>
                            <td>{p.label}</td>
                            <td>{p.domain_curie ?? "—"}</td>
                            <td>{p.range_curie ?? "—"}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </section>
    {/if}

    <!-- Triples -->
    <section class="card">
        <div class="section-header">
            <h2>Triples</h2>
            <span class="count">{triplesTotal.toLocaleString()}</span>
        </div>
        {#if triples.length === 0}
            <p class="empty">No triples found.</p>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>Subject</th>
                        <th>Predicate</th>
                        <th>Object</th>
                    </tr>
                </thead>
                <tbody>
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
                            <td><code class="predicate">{t.predicate}</code></td
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
</style>
