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

    interface ImportResult {
        ontology_id: number;
        entities: number;
        triples: number;
    }

    let { data } = $props();

    let projectOntologies = $state<Ontology[]>(untrack(() => data.projectOntologies));
    const allOntologies: Ontology[] = untrack(() => data.allOntologies);

    // ── Import form ──────────────────────────────────────────────────────────
    let file = $state<File | null>(null);
    let name = $state("");
    let prefix = $state("");
    let baseIri = $state("");
    let version = $state("");
    let submitting = $state(false);
    let importResult = $state<ImportResult | null>(null);
    let importError = $state<string | null>(null);

    async function handleImport(e: SubmitEvent) {
        e.preventDefault();
        if (!file) return;
        submitting = true;
        importResult = null;
        importError = null;
        try {
            const fd = new FormData();
            fd.append("file", file);
            fd.append("name", name);
            fd.append("prefix", prefix);
            fd.append("base_iri", baseIri);
            if (version) fd.append("version", version);

            const res = await fetch("/api/admin/ontology", {
                method: "POST",
                body: fd,
            });
            if (!res.ok) {
                const d = await res.json().catch(() => ({ detail: res.statusText }));
                importError = d.detail ?? res.statusText;
                return;
            }
            const result: ImportResult = await res.json();
            importResult = result;

            // Automatically assign the newly imported ontology to this project
            await fetch(
                `/api/projects/${data.projectId}/ontologies/${result.ontology_id}`,
                { method: "POST" },
            );

            // Immediately reflect in the list
            projectOntologies = [
                ...projectOntologies,
                {
                    ontology_id: result.ontology_id,
                    name,
                    prefix,
                    uri: baseIri,
                    version: version || null,
                },
            ];

            // Reset form
            file = null;
            name = "";
            prefix = "";
            baseIri = "";
            version = "";
        } finally {
            submitting = false;
        }
    }

    // ── Assign existing ──────────────────────────────────────────────────────
    let selectedOntologyId = $state<number | null>(null);
    let assigning = $state(false);
    let assignError = $state<string | null>(null);

    const assignableOntologies = $derived(
        allOntologies.filter(
            (o) => !projectOntologies.some((p) => p.ontology_id === o.ontology_id),
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
                assignError = res.statusText;
                return;
            }
            const added = allOntologies.find((o) => o.ontology_id === selectedOntologyId)!;
            projectOntologies = [...projectOntologies, added];
            selectedOntologyId = null;
        } finally {
            assigning = false;
        }
    }

    // ── Remove ───────────────────────────────────────────────────────────────
    let removingId = $state<number | null>(null);

    async function handleRemove(ontologyId: number) {
        removingId = ontologyId;
        try {
            await fetch(
                `/api/projects/${data.projectId}/ontologies/${ontologyId}`,
                { method: "DELETE" },
            );
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

    <!-- Assigned ontologies -->
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
                                <a href="/projects/{data.projectId}/ontologies/{o.ontology_id}">
                                    {o.name}
                                </a>
                            </td>
                            <td class="uri">{o.uri}</td>
                            <td>{o.version ?? "—"}</td>
                            <td>
                                <button
                                    class="btn-danger-sm"
                                    disabled={removingId === o.ontology_id}
                                    onclick={() => handleRemove(o.ontology_id)}
                                >
                                    {removingId === o.ontology_id ? "Removing…" : "Remove"}
                                </button>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        {/if}

        {#if assignableOntologies.length > 0}
            <div class="assign-row">
                <select bind:value={selectedOntologyId}>
                    <option value={null}>Add existing ontology…</option>
                    {#each assignableOntologies as o (o.ontology_id)}
                        <option value={o.ontology_id}>{o.prefix} — {o.name}</option>
                    {/each}
                </select>
                <button
                    class="btn-primary-sm"
                    disabled={!selectedOntologyId || assigning}
                    onclick={handleAssign}
                >
                    {assigning ? "Adding…" : "Add"}
                </button>
                {#if assignError}<span class="error">{assignError}</span>{/if}
            </div>
        {/if}
    </section>

    <!-- Import OWL -->
    <section class="card">
        <h2>Import OWL ontology</h2>
        <form onsubmit={handleImport}>
            <div class="field">
                <label for="ont-file">OWL file</label>
                <input
                    id="ont-file"
                    type="file"
                    accept=".owl,.rdf,.xml,.ttl"
                    required
                    onchange={(e) => {
                        file = (e.target as HTMLInputElement).files?.[0] ?? null;
                    }}
                />
            </div>
            <div class="fields-row">
                <div class="field">
                    <label for="ont-name">Name</label>
                    <input id="ont-name" type="text" bind:value={name} required placeholder="NCBI Taxonomy" />
                </div>
                <div class="field">
                    <label for="ont-prefix">Prefix</label>
                    <input id="ont-prefix" type="text" bind:value={prefix} required placeholder="NCBITaxon" />
                </div>
            </div>
            <div class="fields-row">
                <div class="field">
                    <label for="ont-iri">Base IRI <span class="optional">(optional)</span></label>
                    <input id="ont-iri" type="text" bind:value={baseIri} placeholder="http://purl.obolibrary.org/obo/" />
                </div>
                <div class="field">
                    <label for="ont-version">Version <span class="optional">(optional)</span></label>
                    <input id="ont-version" type="text" bind:value={version} placeholder="2024-01-01" />
                </div>
            </div>

            {#if importError}
                <p class="error">{importError}</p>
            {/if}
            {#if importResult}
                <p class="success">
                    Imported {importResult.entities} entities and {importResult.triples} triples.
                    Ontology assigned to this project.
                </p>
            {/if}

            <button type="submit" class="btn-primary" disabled={submitting}>
                {submitting ? "Importing…" : "Import and assign"}
            </button>
        </form>
    </section>
</div>

<style>
    .field {
        flex: 1;
    }

    .fields-row {
        display: flex;
        gap: 1rem;
    }

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

    input[type="text"],
    input[type="file"] {
        padding: 0.4rem 0.5rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.9rem;
        width: 100%;
        box-sizing: border-box;
    }

    .optional {
        font-weight: 400;
        text-transform: none;
        letter-spacing: 0;
        color: #888;
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
