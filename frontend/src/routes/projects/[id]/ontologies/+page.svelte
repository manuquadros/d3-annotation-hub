<script lang="ts">
    import { untrack } from "svelte";
    import "$lib/styles/management.css";
    import OntologyImportForm from "$lib/components/OntologyImportForm.svelte";
    import type { ImportedResult } from "$lib/components/OntologyImportForm.svelte";
    import { errorDetail } from "$lib/utils/http";

    interface Ontology {
        ontology_id: number;
        name: string;
        prefix: string;
        uri: string | null;
        version: string | null;
    }

    let { data } = $props();

    let projectOntologies = $state<Ontology[]>(
        untrack(() => data.projectOntologies),
    );
    const allOntologies: Ontology[] = untrack(() => data.allOntologies);

    async function handleImported(result: ImportedResult) {
        const res = await fetch(
            `/api/projects/${data.projectId}/ontologies/${result.ontology_id}`,
            { method: "POST" },
        );
        if (!res.ok) {
            throw new Error(await errorDetail(res));
        }
        projectOntologies = [
            ...projectOntologies,
            {
                ontology_id: result.ontology_id,
                name: result.name,
                prefix: result.prefix,
                uri: result.uri,
                version: result.version,
            },
        ];
    }

    let selectedOntologyId = $state<number | null>(null);
    let assigning = $state(false);
    let assignError = $state<string | null>(null);

    const assignableOntologies = $derived(
        allOntologies.filter(
            (o) =>
                !projectOntologies.some((p) => p.ontology_id === o.ontology_id),
        ),
    );

    async function handleAssign() {
        if (!selectedOntologyId) return;
        assigning = true;
        assignError = null;
        try {
            const res = await fetch(
                `/api/projects/${data.projectId}/ontologies/${selectedOntologyId}`,
                { method: "POST" },
            );
            if (!res.ok) {
                assignError = await errorDetail(res);
                return;
            }
            const added = allOntologies.find(
                (o) => o.ontology_id === selectedOntologyId,
            )!;
            projectOntologies = [...projectOntologies, added];
            selectedOntologyId = null;
        } finally {
            assigning = false;
        }
    }

    let removingId = $state<number | null>(null);
    let removeError = $state<string | null>(null);

    async function handleRemove(ontologyId: number) {
        removingId = ontologyId;
        removeError = null;
        try {
            const res = await fetch(
                `/api/projects/${data.projectId}/ontologies/${ontologyId}`,
                { method: "DELETE" },
            );
            if (!res.ok) {
                removeError = await errorDetail(res);
                return;
            }
            projectOntologies = projectOntologies.filter(
                (o) => o.ontology_id !== ontologyId,
            );
        } finally {
            removingId = null;
        }
    }
</script>

<div class="page">
    <h1>Ontologies</h1>

    <section class="card">
        <h2>Assigned to this project</h2>
        {#if projectOntologies.length === 0}
            <p class="empty">No ontologies assigned yet.</p>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>Prefix</th>
                        <th>Name</th>
                        <th>URI</th>
                        <th>Version</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {#each projectOntologies as o (o.ontology_id)}
                        <tr>
                            <td><code>{o.prefix}</code></td>
                            <td>
                                <a
                                    href="/projects/{data.projectId}/ontologies/{o.ontology_id}"
                                >
                                    {o.name}
                                </a>
                            </td>
                            <td class="uri">{o.uri}</td>
                            <td>{o.version ?? "—"}</td>
                            <td>
                                <button
                                    class="btn small danger filled"
                                    disabled={removingId === o.ontology_id}
                                    onclick={() => handleRemove(o.ontology_id)}
                                >
                                    {removingId === o.ontology_id
                                        ? "Removing…"
                                        : "Remove"}
                                </button>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        {/if}

        {#if removeError}<p class="error">{removeError}</p>{/if}

        {#if assignableOntologies.length > 0}
            <div class="assign-row">
                <select bind:value={selectedOntologyId}>
                    <option value={null}>Add existing ontology…</option>
                    {#each assignableOntologies as o (o.ontology_id)}
                        <option value={o.ontology_id}
                            >{o.prefix} — {o.name}</option
                        >
                    {/each}
                </select>
                <button
                    class="btn small primary filled"
                    disabled={!selectedOntologyId || assigning}
                    onclick={handleAssign}
                >
                    {assigning ? "Adding…" : "Add"}
                </button>
                {#if assignError}<span class="error">{assignError}</span>{/if}
            </div>
        {/if}
    </section>

    <section class="card">
        <h2>Import OWL ontology</h2>
        <OntologyImportForm
            submitLabel="Import and assign"
            onimported={handleImported}
        />
    </section>
</div>

<style>
    .assign-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding-top: 0.5rem;
        border-top: 1px solid #eee;
    }

    .assign-row select {
        flex: 1;
        padding: 0.35rem 0.5rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.9rem;
    }

    td.uri {
        font-size: 0.85rem;
        color: #666;
        max-width: 260px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
