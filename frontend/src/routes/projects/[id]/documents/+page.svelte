<script lang="ts">
    import { untrack } from "svelte";
    import { SvelteSet } from "svelte/reactivity";
    import "$lib/styles/management.css";
    import { errorDetail } from "$lib/utils/http";
    interface Reference {
        reference_id: number;
        pubmed_id: number | null;
        doi: string | null;
        title: string;
        authors: string;
        year: number;
    }

    interface Result {
        imported: number;
        already_in_project: number;
        not_found: string[];
    }

    let { data } = $props();

    let references = $state<Reference[]>(untrack(() => data.references));
    let input = $state("");
    let submitting = $state(false);
    let result = $state<Result | null>(null);
    let errorMessage = $state<string | null>(null);
    const removing = new SvelteSet<number>();

    async function handleRemove(referenceId: number) {
        removing.add(referenceId);
        try {
            const res = await fetch(
                `/api/projects/${data.projectId}/references/${referenceId}`,
                { method: "DELETE" },
            );
            if (res.ok) {
                references = references.filter(
                    (r) => r.reference_id !== referenceId,
                );
            } else {
                errorMessage = `Failed to remove reference: ${await errorDetail(res)}`;
            }
        } catch (err) {
            errorMessage = String(err);
        } finally {
            removing.delete(referenceId);
        }
    }

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
            const res = await fetch(
                `/api/projects/${data.projectId}/references`,
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ identifiers }),
                },
            );

            if (!res.ok) {
                errorMessage = await errorDetail(res);
            } else {
                result = await res.json();
                if (result!.imported > 0) {
                    input = "";
                    const listRes = await fetch(
                        `/api/projects/${data.projectId}/references`,
                    );
                    if (listRes.ok) references = await listRes.json();
                }
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
                placeholder="36828727&#10;10.1038/s41586-023-05881-4&#10;37001221"
                rows={6}
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
                            <span class="monospace"
                                >{result.not_found.join(", ")}</span
                            >
                        </p>
                    {/if}
                </div>
            {/if}

            <button
                type="submit"
                class="btn primary filled"
                disabled={submitting || !input.trim()}
            >
                {submitting ? "Importing…" : "Import references"}
            </button>
        </form>
    </section>

    {#if references.length > 0}
        <section class="card">
            <h2>Documents in this project ({references.length})</h2>
            <table>
                <thead>
                    <tr>
                        <th>Identifier</th>
                        <th>Title</th>
                        <th>Authors</th>
                        <th>Year</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {#each references as ref (ref.reference_id)}
                        <tr>
                            <td class="monospace doi">
                                {#if ref.doi}
                                    {ref.doi}
                                {:else if ref.pubmed_id}
                                    PMID:{ref.pubmed_id}
                                {:else}
                                    —
                                {/if}
                            </td>
                            <td class="title">{ref.title}</td>
                            <td class="authors">{ref.authors}</td>
                            <td class="year">{ref.year}</td>
                            <td class="remove-cell">
                                <button
                                    class="remove-btn"
                                    onclick={() =>
                                        handleRemove(ref.reference_id)}
                                    disabled={removing.has(ref.reference_id)}
                                    title="Remove from project"
                                    aria-label="Remove {ref.title} from project"
                                    >×</button
                                >
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </section>
    {/if}
</div>

<style>
    textarea {
        width: 100%;
        padding: 0.5rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.9rem;
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
        font-size: 0.9rem;
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

    .monospace {
        font-family: monospace;
    }

    td.doi {
        font-size: 0.85rem;
        color: #555;
        white-space: nowrap;
    }

    td.title {
        font-weight: 500;
    }

    td.authors {
        color: #555;
        font-size: 0.85rem;
    }

    td.year {
        white-space: nowrap;
        color: #555;
    }

    td.remove-cell {
        width: 1px;
        padding: 0 0.25rem;
        text-align: center;
    }

    .remove-btn {
        background: none;
        border: none;
        cursor: pointer;
        color: #aaa;
        font-size: 1.1rem;
        line-height: 1;
        padding: 0.1rem 0.3rem;
        border-radius: 3px;
        transition:
            color 0.15s,
            background 0.15s;
    }

    .remove-btn:hover:not(:disabled) {
        color: #c0392b;
        background: #fdecea;
    }

    .remove-btn:disabled {
        opacity: 0.4;
        cursor: default;
    }
</style>
