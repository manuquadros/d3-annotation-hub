<script lang="ts">
    import { goto } from "$app/navigation";
    import { setLastProject } from "$lib/api";
    import { errorDetail } from "$lib/utils/http";

    let name = $state("");
    let description = $state("");
    let requiredAnnotators = $state(2);
    let errorMessage = $state<string | null>(null);
    let submitting = $state(false);

    async function handleSubmit(e: SubmitEvent) {
        e.preventDefault();
        submitting = true;
        errorMessage = null;
        try {
            const res = await fetch("/api/projects", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name,
                    description: description || null,
                    required_annotators: requiredAnnotators,
                }),
            });
            if (!res.ok) {
                errorMessage = await errorDetail(res);
            } else {
                const created = await res.json();
                await setLastProject(created.project_id);
                goto(`/?project=${created.project_id}`);
            }
        } catch (err) {
            errorMessage = String(err);
        } finally {
            submitting = false;
        }
    }
</script>

<div class="new-project-page">
    <h1>New Project</h1>

    <div class="card">
        <form onsubmit={handleSubmit}>
            <div class="field">
                <label for="proj-name">Name</label>
                <!-- svelte-ignore a11y_autofocus -->
                <input
                    id="proj-name"
                    type="text"
                    bind:value={name}
                    placeholder="My Annotation Project"
                    required
                    autofocus
                />
            </div>

            <div class="field">
                <label for="proj-desc">
                    Description <span class="optional">(optional)</span>
                </label>
                <input
                    id="proj-desc"
                    type="text"
                    bind:value={description}
                    placeholder="Short description"
                />
            </div>

            <div class="field field-narrow">
                <label for="proj-annotators"
                    >Required annotators per document</label
                >
                <input
                    id="proj-annotators"
                    type="number"
                    min="1"
                    bind:value={requiredAnnotators}
                />
            </div>

            {#if errorMessage}
                <p class="error">{errorMessage}</p>
            {/if}

            <div class="actions">
                <button
                    type="submit"
                    class="btn primary filled"
                    disabled={submitting}
                >
                    {submitting ? "Creating…" : "Create project"}
                </button>
                <a href="/admin" class="btn secondary">Cancel</a>
            </div>
        </form>
    </div>
</div>

<style>
    .new-project-page {
        max-width: 480px;
        margin: 2rem auto;
        padding: 0 1rem;
    }

    h1 {
        font-size: 1.4rem;
        margin-bottom: 1.5rem;
    }

    .card {
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
    }

    .field {
        margin-bottom: 1.2rem;
    }

    .field-narrow {
        max-width: 160px;
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
    input[type="number"] {
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        box-sizing: border-box;
    }

    .error {
        color: #c00;
        font-size: 0.875rem;
        margin: 0 0 1rem;
    }

    .actions {
        display: flex;
        gap: 0.75rem;
        align-items: center;
        margin-top: 1.5rem;
    }
</style>
