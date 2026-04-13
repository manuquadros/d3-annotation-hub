<script lang="ts">
    import { page } from "$app/stores";

    const projectId = $derived(Number($page.params.id));

    let input = $state("");
    let submitting = $state(false);

    interface Result {
        imported: number;
        already_in_project: number;
        not_found: string[];
    }

    let result = $state<Result | null>(null);
    let errorMessage = $state<string | null>(null);

    async function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        submitting = true;
        result = null;
        errorMessage = null;

        const identifiers = input
            .split(/[\n,]+/)
            .map((s) => s.trim())
            .filter(Boolean);

        if (identifiers.length === 0) {
            submitting = false;
            return;
        }

        try {
            const res = await fetch(`/api/projects/${projectId}/references`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ identifiers }),
            });

            if (!res.ok) {
                const d = await res.json().catch(() => ({ detail: res.statusText }));
                errorMessage = d.detail ?? res.statusText;
            } else {
                result = await res.json();
                if (result!.imported > 0) input = "";
            }
        } catch (err) {
            errorMessage = String(err);
        } finally {
            submitting = false;
        }
    }
</script>

<div class="page">
    <h1>Documents</h1>

    <section class="card">
        <p class="hint">
            Enter PubMed IDs or DOIs (one per line, or comma-separated).
            Matching references already in the database will be added to this
            project's annotation queue.
        </p>

        <form onsubmit={handleSubmit}>
            <textarea
                bind:value={input}
                placeholder={"36828727\n10.1038/s41586-023-05881-4\n37001221"}
                rows={8}
                disabled={submitting}
            ></textarea>

            {#if errorMessage}
                <p class="error">{errorMessage}</p>
            {/if}

            {#if result}
                <div class="feedback">
                    <p>
                        {result.imported === 1
                            ? "1 reference imported into the project."
                            : `${result.imported} references imported into the project.`}
                    </p>
                    {#if result.already_in_project > 0}
                        <p>
                            {result.already_in_project === 1
                                ? "1 reference was already in the project and was not imported again."
                                : `${result.already_in_project} references were already in the project and were not imported again.`}
                        </p>
                    {/if}
                    {#if result.not_found.length > 0}
                        <p class="warn">
                            {result.not_found.length === 1
                                ? "1 identifier was not found in the database:"
                                : `${result.not_found.length} identifiers were not found in the database:`}
                            <span class="not-found-list">{result.not_found.join(", ")}</span>
                        </p>
                    {/if}
                </div>
            {/if}

            <button type="submit" class="btn-primary" disabled={submitting || !input.trim()}>
                {submitting ? "Importing…" : "Import references"}
            </button>
        </form>
    </section>
</div>

<style>
    .page {
        max-width: 640px;
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

    .hint {
        font-size: 0.875rem;
        color: #555;
        margin: 0;
    }

    textarea {
        width: 100%;
        padding: 0.5rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        font-family: monospace;
        resize: vertical;
        box-sizing: border-box;
    }

    textarea:disabled {
        background: #f5f5f5;
    }

    .feedback {
        background: #f0f7f0;
        border: 1px solid #c3dfc3;
        border-radius: 4px;
        padding: 0.75rem 1rem;
        font-size: 0.875rem;
    }

    .feedback p {
        margin: 0 0 0.25rem;
    }

    .feedback p:last-child {
        margin-bottom: 0;
    }

    .warn {
        color: #7a5500;
    }

    .not-found-list {
        font-family: monospace;
    }

    .error {
        color: #c00;
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
</style>
