<script lang="ts">
    import "$lib/styles/management.css";
    import {
        computeOverallPct,
        type ImportStep,
    } from "$lib/utils/importProgress";

    export interface ImportedResult {
        ontology_id: number;
        entities: number;
        triples: number;
        properties: number;
        name: string;
        prefix: string;
        uri: string | null;
        version: string | null;
    }

    interface Props {
        submitLabel?: string;
        onimported?: (result: ImportedResult) => void | Promise<void>;
    }

    let { submitLabel = "Import", onimported }: Props = $props();

    const STEP_ORDER = [
        "parse",
        "store_ontology",
        "load_entities",
        "load_triples",
        "load_properties",
    ] as const;

    const STEP_LABELS: Record<string, string> = {
        parse: "Parse OWL file",
        store_ontology: "Store ontology metadata",
        load_entities: "Load classes",
        load_triples: "Load triples",
        load_properties: "Load properties",
    };

    const BINARY_STEPS = new Set(["parse", "store_ontology"]);

    async function* readSSE(
        body: ReadableStream<Uint8Array>,
    ): AsyncGenerator<{ event: string; data: string }> {
        const reader = body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const messages = buffer.split("\n\n");
                buffer = messages.pop() ?? "";
                for (const message of messages) {
                    if (!message.trim()) continue;
                    let eventType = "message";
                    let dataLine = "";
                    for (const line of message.split("\n")) {
                        if (line.startsWith("event: "))
                            eventType = line.slice(7).trim();
                        if (line.startsWith("data: "))
                            dataLine = line.slice(6).trim();
                    }
                    if (dataLine) yield { event: eventType, data: dataLine };
                }
            }
        } finally {
            reader.releaseLock();
        }
    }

    let file = $state<File | null>(null);
    let name = $state("");
    let prefix = $state("");
    let baseIri = $state("");
    let version = $state("");
    // Tracks which fields were auto-filled from the filename or peek vs. typed
    // by the user. Auto-filled fields are cleared when a new file is selected
    // so the new file's peek can repopulate them; user-typed fields are not.
    let autoFilled = new Set<"name" | "prefix" | "baseIri" | "version">();
    // Monotonically increasing counter; each peekFile call captures the value
    // at call time and checks it before applying results to discard stale
    // responses from previously selected files.
    let peekSeq = 0;

    // Turtle/RDF-XML/JSON-LD ontologies can only be parsed as a whole, so the
    // entire file is sent for the metadata peek. Files larger than this are not
    // peeked (the user fills the fields manually) to avoid a large upload and a
    // slow parse. Must match d3textdb.owl.MAX_PEEK_BYTES.
    const MAX_PEEK_BYTES = 50 * 1024 * 1024;

    async function peekFile(f: File) {
        const mySeq = ++peekSeq;
        if (f.size > MAX_PEEK_BYTES) return;
        const form = new FormData();
        form.append("file", f, f.name);
        try {
            const res = await fetch("/api/admin/ontology/peek", {
                method: "POST",
                body: form,
            });
            if (mySeq !== peekSeq) return;
            if (!res.ok) return;
            const meta: {
                name: string | null;
                prefix: string | null;
                base_iri: string | null;
                version: string | null;
            } = await res.json();
            // Re-check after the json() await: a newer file may have been selected
            // while the body was being read, which would make this response stale.
            if (mySeq !== peekSeq) return;
            if (meta.name && (!name || autoFilled.has("name"))) {
                name = meta.name;
                autoFilled.add("name");
            }
            if (meta.prefix && (!prefix || autoFilled.has("prefix"))) {
                prefix = meta.prefix;
                autoFilled.add("prefix");
            }
            if (meta.version && (!version || autoFilled.has("version"))) {
                version = meta.version;
                autoFilled.add("version");
            }
            if (meta.base_iri && (!baseIri || autoFilled.has("baseIri"))) {
                baseIri = meta.base_iri;
                autoFilled.add("baseIri");
            }
        } catch {
            // best-effort; form still works without it
        }
    }

    let submitting = $state(false);
    let result = $state<ImportedResult | null>(null);
    let errorMessage = $state<string | null>(null);
    let importSteps = $state<ImportStep[]>([]);
    let overallPct = $derived(computeOverallPct(importSteps));

    async function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        if (!file) return;
        ++peekSeq;

        submitting = true;
        result = null;
        errorMessage = null;
        importSteps = STEP_ORDER.map((step) => ({
            step,
            label: STEP_LABELS[step],
            status: "pending" as const,
            counts: { loaded: 0, total: 0 },
            isBinary: BINARY_STEPS.has(step),
        }));

        const form = new FormData();
        form.append("file", file);
        form.append("name", name);
        form.append("prefix", prefix);
        form.append("base_iri", baseIri);
        if (version) form.append("version", version);

        const snapshot = {
            name,
            prefix,
            uri: baseIri || null,
            version: version || null,
        };

        try {
            const res = await fetch("/api/admin/ontology", {
                method: "POST",
                body: form,
            });

            if (!res.ok || !res.body) {
                const detail = await res
                    .json()
                    .catch(() => ({ detail: res.statusText }));
                errorMessage = detail.detail ?? res.statusText;
                importSteps = [];
                return;
            }

            for await (const { event, data } of readSSE(res.body)) {
                if (event === "progress") {
                    const p = JSON.parse(data) as {
                        step: string;
                        loaded: number;
                        total: number;
                    };
                    importSteps = importSteps.map((s) => {
                        if (s.step === p.step) {
                            const done = p.loaded >= p.total && p.total > 0;
                            return {
                                ...s,
                                status: done ? "done" : "active",
                                counts: { loaded: p.loaded, total: p.total },
                            };
                        }
                        if (
                            s.status === "active" &&
                            STEP_ORDER.indexOf(
                                s.step as (typeof STEP_ORDER)[number],
                            ) <
                                STEP_ORDER.indexOf(
                                    p.step as (typeof STEP_ORDER)[number],
                                )
                        ) {
                            return { ...s, status: "done" };
                        }
                        return s;
                    });
                } else if (event === "complete") {
                    const raw = JSON.parse(data) as {
                        ontology_id: number;
                        entities: number;
                        triples: number;
                        properties: number;
                    };
                    result = { ...raw, ...snapshot };
                    importSteps = importSteps.map((s) => ({
                        ...s,
                        status: "done",
                    }));
                    await onimported?.(result);
                    file = null;
                    name = "";
                    prefix = "";
                    baseIri = "";
                    version = "";
                    autoFilled.clear();
                } else if (event === "error") {
                    const { detail } = JSON.parse(data) as { detail: string };
                    importSteps = importSteps.map((s) =>
                        s.status === "active" ? { ...s, status: "error" } : s,
                    );
                    errorMessage = detail;
                    break;
                }
            }
            if (!result && !errorMessage) {
                errorMessage =
                    "Import was interrupted before completing — check the database for partial data.";
                importSteps = importSteps.map((s) =>
                    s.status === "active" ? { ...s, status: "error" } : s,
                );
            }
        } catch (err) {
            result = null;
            errorMessage = err instanceof Error ? err.message : String(err);
            importSteps = importSteps.map((s) =>
                s.status === "active" ? { ...s, status: "error" } : s,
            );
        } finally {
            submitting = false;
        }
    }
</script>

<form onsubmit={handleSubmit}>
    <div class="field">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label>OWL file</label>
        <div class="custom-file">
            <input
                id="owl-file"
                type="file"
                accept=".owl,.rdf,.ttl,.nt,.n3,.jsonld,.xml"
                onchange={(e) => {
                    const newFile =
                        (e.currentTarget as HTMLInputElement).files?.[0] ??
                        null;
                    if (newFile) {
                        if (autoFilled.has("name")) name = "";
                        if (autoFilled.has("prefix")) prefix = "";
                        if (autoFilled.has("baseIri")) baseIri = "";
                        if (autoFilled.has("version")) version = "";
                        autoFilled.clear();
                        file = newFile;
                        if (!name) {
                            name = file.name.replace(/\.[^.]+$/, "");
                            autoFilled.add("name");
                        }
                        peekFile(file);
                    } else {
                        file = null;
                        autoFilled.clear();
                    }
                }}
                required
            />
            <label for="owl-file">Browse…</label>
            <span class="file-names">{file?.name ?? "No file chosen"}</span>
        </div>
    </div>

    <div class="field-row">
        <div class="field">
            <label for="onto-name">Name</label>
            <input
                id="onto-name"
                type="text"
                class="form-control small"
                bind:value={name}
                oninput={() => {
                    autoFilled.delete("name");
                }}
                placeholder="NCBI Taxonomy"
                required
            />
        </div>
        <div class="field">
            <label for="onto-prefix">Prefix</label>
            <input
                id="onto-prefix"
                type="text"
                class="form-control small"
                bind:value={prefix}
                oninput={() => {
                    autoFilled.delete("prefix");
                }}
                placeholder="NCBITaxon"
                required
            />
        </div>
    </div>

    <div class="field">
        <label for="onto-version"
            >Version <span class="optional">(optional)</span></label
        >
        <input
            id="onto-version"
            type="text"
            class="form-control small"
            bind:value={version}
            oninput={() => {
                autoFilled.delete("version");
            }}
            placeholder="2024-01-01"
        />
    </div>

    <div class="field">
        <label for="base-iri">
            Base IRI <span class="optional"
                >(leave empty for OBO Foundry ontologies)</span
            >
        </label>
        <input
            id="base-iri"
            type="text"
            class="form-control small"
            bind:value={baseIri}
            oninput={() => {
                autoFilled.delete("baseIri");
            }}
            placeholder="https://example.org/ontology/"
        />
    </div>

    {#if importSteps.length > 0}
        <div class="import-progress">
            <progress value={overallPct} max={100}></progress>
            <span class="pct">{overallPct}%</span>
        </div>
        <div class="import-steps">
            {#each importSteps as s (s.step)}
                <div class="import-step {s.status}">
                    <span class="step-icon">
                        {#if s.status === "done"}✓
                        {:else if s.status === "error"}✗
                        {:else if s.status === "active"}…
                        {:else}·{/if}
                    </span>
                    <span class="step-label">{s.label}</span>
                    {#if s.status === "active" && !s.isBinary && s.counts.total > 0}
                        <span class="step-count">
                            {s.counts.loaded.toLocaleString()}/{s.counts.total.toLocaleString()}
                        </span>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}

    {#if errorMessage}
        <p class="error">{errorMessage}</p>
    {/if}

    {#if result}
        <p class="success">
            Imported {result.entities.toLocaleString()} entities,
            {result.triples.toLocaleString()} triples, and
            {result.properties.toLocaleString()} properties (ontology #{result.ontology_id}).
        </p>
    {/if}

    <div class="actions">
        <button
            type="submit"
            class="btn primary filled"
            disabled={submitting || !file}
        >
            {submitting ? "Importing…" : submitLabel}
        </button>
    </div>
</form>

<style>
    form {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .import-progress {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-top: 0.25rem;
    }

    .import-progress progress {
        flex: 1;
        height: 6px;
    }

    .import-progress .pct {
        font-size: 0.8rem;
        color: #888;
        min-width: 2.5rem;
        text-align: right;
    }

    .import-steps {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
        font-size: 0.825rem;
    }

    .import-step {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: #bbb;
    }

    .import-step.active {
        color: #333;
        font-weight: 600;
    }

    .import-step.done {
        color: #080;
    }

    .import-step.error {
        color: #c00;
    }

    .step-icon {
        width: 1rem;
        text-align: center;
    }

    .step-count {
        margin-left: auto;
        font-variant-numeric: tabular-nums;
        color: #888;
        font-weight: 400;
    }

    .actions {
        margin-top: 0.5rem;
    }

    /* Digidive .custom-file label inherits management.css .field label uppercase — reset it */
    .custom-file label {
        font-size: 0.9rem;
        font-weight: 400;
        text-transform: none;
        letter-spacing: 0;
    }

    /* Make .custom-file a flex row so .file-names can flex-shrink and show ellipsis */
    .custom-file {
        display: flex;
        align-items: center;
    }

    .file-names {
        flex: 1;
        min-width: 0;
        font-size: 0.875rem;
        color: #666;
        margin-left: 0.6rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
</style>
