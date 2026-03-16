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
    let ontologies = $state<Ontology[]>(data.ontologies);

    // ── Form state ────────────────────────────────────────────────────────────
    let file = $state<File | null>(null);
    let name = $state("");
    let prefix = $state("");
    let baseIri = $state("");
    let version = $state("");

    let submitting = $state(false);
    let result = $state<ImportResult | null>(null);
    let errorMessage = $state<string | null>(null);

    async function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        if (!file) return;

        submitting = true;
        result = null;
        errorMessage = null;

        const form = new FormData();
        form.append("file", file);
        form.append("name", name);
        form.append("prefix", prefix);
        form.append("base_iri", baseIri);
        if (version) form.append("version", version);

        try {
            const res = await fetch("/api/admin/ontology", {
                method: "POST",
                body: form,
            });
            if (!res.ok) {
                const detail = await res.json().catch(() => ({ detail: res.statusText }));
                errorMessage = detail.detail ?? res.statusText;
            } else {
                result = await res.json();
                // Refresh ontology list
                const listRes = await fetch("/api/admin/ontology");
                if (listRes.ok) ontologies = await listRes.json();
                // Reset form
                file = null;
                name = "";
                prefix = "";
                baseIri = "";
                version = "";
            }
        } catch (err) {
            errorMessage = String(err);
        } finally {
            submitting = false;
        }
    }
</script>

<div class="admin-page">
    <h1>Ontology Management</h1>

    <section class="card">
        <h2>Import OWL Ontology</h2>
        <form onsubmit={handleSubmit}>
            <div class="field">
                <label for="owl-file">OWL file</label>
                <input
                    id="owl-file"
                    type="file"
                    accept=".owl,.rdf,.ttl,.nt,.n3,.jsonld"
                    onchange={(e) => {
                        file = (e.currentTarget as HTMLInputElement).files?.[0] ?? null;
                        if (file && !name) name = file.name.replace(/\.[^.]+$/, "");
                    }}
                    required
                />
            </div>

            <div class="field-row">
                <div class="field">
                    <label for="onto-name">Name</label>
                    <input id="onto-name" type="text" bind:value={name} placeholder="NCBI Taxonomy" required />
                </div>
                <div class="field">
                    <label for="onto-prefix">Prefix</label>
                    <input id="onto-prefix" type="text" bind:value={prefix} placeholder="NCBITaxon" required />
                </div>
            </div>

            <div class="field">
                <label for="onto-version">Version <span class="optional">(optional)</span></label>
                <input id="onto-version" type="text" bind:value={version} placeholder="2024-01-01" />
            </div>

            <div class="field">
                <label for="base-iri">
                    Base IRI <span class="optional">(leave empty for OBO Foundry ontologies)</span>
                </label>
                <input
                    id="base-iri"
                    type="text"
                    bind:value={baseIri}
                    placeholder="https://example.org/ontology/"
                />
            </div>

            {#if errorMessage}
                <p class="error">{errorMessage}</p>
            {/if}

            {#if result}
                <p class="success">
                    Imported {result.entities.toLocaleString()} entities and
                    {result.triples.toLocaleString()} triples
                    (ontology #{result.ontology_id}).
                </p>
            {/if}

            <div class="actions">
                <button type="submit" class="btn-primary" disabled={submitting || !file}>
                    {submitting ? "Importing…" : "Import"}
                </button>
            </div>
        </form>
    </section>

    <section class="card">
        <h2>Loaded Ontologies</h2>
        {#if ontologies.length === 0}
            <p class="empty">No ontologies loaded yet.</p>
        {:else}
            <table>
                <thead>
                    <tr>
                        <th>Prefix</th>
                        <th>Name</th>
                        <th>URI</th>
                        <th>Version</th>
                    </tr>
                </thead>
                <tbody>
                    {#each ontologies as onto}
                        <tr>
                            <td><code>{onto.prefix}</code></td>
                            <td>{onto.name}</td>
                            <td class="uri">{onto.uri}</td>
                            <td>{onto.version ?? "—"}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        {/if}
    </section>
</div>

<style>
    .admin-page {
        max-width: 860px;
        margin: 2rem auto;
        padding: 0 1rem;
    }

    h1 {
        font-size: 1.4rem;
        margin-bottom: 1.5rem;
    }

    h2 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 1.2rem;
    }

    .card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .field {
        margin-bottom: 1rem;
    }

    .field-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    label {
        display: block;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #444;
        margin-bottom: 0.3rem;
    }

    .optional {
        font-weight: 400;
        text-transform: none;
        letter-spacing: 0;
        color: #888;
    }

    input[type="text"],
    input[type="file"] {
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        box-sizing: border-box;
    }

    input[type="file"] {
        padding: 0.3rem;
    }

    .actions {
        margin-top: 1.2rem;
    }

    .btn-primary {
        padding: 0.5rem 1.2rem;
        background: #333;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.875rem;
    }

    .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .btn-primary:not(:disabled):hover {
        background: #111;
    }

    .error {
        color: #c00;
        font-size: 0.875rem;
        margin: 0.5rem 0 0;
    }

    .success {
        color: #080;
        font-size: 0.875rem;
        margin: 0.5rem 0 0;
    }

    .empty {
        color: #888;
        font-size: 0.875rem;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
    }

    th {
        text-align: left;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #666;
        padding: 0.4rem 0.6rem;
        border-bottom: 2px solid #eee;
    }

    td {
        padding: 0.5rem 0.6rem;
        border-bottom: 1px solid #f0f0f0;
        vertical-align: top;
    }

    .uri {
        color: #555;
        font-size: 0.8rem;
        word-break: break-all;
    }

    code {
        background: #f0f0f0;
        padding: 0.1em 0.3em;
        border-radius: 3px;
        font-size: 0.85em;
    }
</style>
