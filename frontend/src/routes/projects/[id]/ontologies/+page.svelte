<script lang="ts">
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

    let projectOntologies = $state<Ontology[]>(data.projectOntologies);
    const allOntologies: Ontology[] = data.allOntologies;

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
                            <td>{o.name}</td>
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
    .page {
        max-width: 860px;
        margin: 2rem auto;
        padding: 0 1rem;
        display: flex;
        flex-direction: column;
        gap: 2rem;
    }

    h1 {
        font-size: 1.4rem;
        margin: 0;
    }

    .card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    h2 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
    }

    th {
        text-align: left;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #666;
        padding: 0.4rem 0.5rem;
        border-bottom: 1px solid #eee;
    }

    td {
        padding: 0.5rem;
        border-bottom: 1px solid #f5f5f5;
        vertical-align: middle;
    }

    td.uri {
        font-size: 0.8rem;
        color: #666;
        max-width: 260px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
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
        font-size: 0.875rem;
    }

    .field {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        flex: 1;
    }

    .fields-row {
        display: flex;
        gap: 1rem;
    }

    label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #444;
    }

    .optional {
        font-weight: 400;
        text-transform: none;
        letter-spacing: 0;
        color: #888;
    }

    input[type="text"],
    input[type="file"] {
        padding: 0.4rem 0.5rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        width: 100%;
        box-sizing: border-box;
    }

    .empty {
        font-size: 0.875rem;
        color: #888;
        margin: 0;
    }

    .error {
        color: #c00;
        font-size: 0.875rem;
        margin: 0;
    }

    .success {
        color: #2a7a2a;
        font-size: 0.875rem;
        margin: 0;
    }

    .btn-primary {
        padding: 0.5rem 1.2rem;
        background: #333;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.875rem;
        align-self: flex-start;
    }

    .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-primary:not(:disabled):hover {
        background: #111;
    }

    .btn-primary-sm {
        padding: 0.35rem 0.8rem;
        background: #333;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.8rem;
        white-space: nowrap;
    }

    .btn-primary-sm:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-danger-sm {
        padding: 0.25rem 0.6rem;
        background: none;
        color: #c00;
        border: 1px solid #c00;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.8rem;
    }

    .btn-danger-sm:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-danger-sm:not(:disabled):hover {
        background: #fee;
    }
</style>
