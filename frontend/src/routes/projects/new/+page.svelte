<script lang="ts">
    import { goto } from "$app/navigation";
    import { setLastProject } from "$lib/api";
    import "$lib/styles/management.css";
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

<div class="page">
    <h1>New Project</h1>

    <div class="card">
        <form onsubmit={handleSubmit}>
            <div class="field">
                <label for="proj-name">Name</label>
                <!-- svelte-ignore a11y_autofocus -->
                <input
                    id="proj-name"
                    class="form-control small"
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
                    class="form-control small"
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
                    class="form-control small"
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
    /* Shared `.page` is 900px, which strands this short single-column form.
       The narrow measure is a deliberate page-specific override, not a
       leftover private copy of the design system. */
    .page {
        max-width: 480px;
    }

    form {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .field-narrow {
        max-width: 160px;
    }

    .actions {
        display: flex;
        gap: 0.75rem;
        align-items: center;
        margin-top: 0.75rem;
    }
</style>
