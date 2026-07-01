<script lang="ts">
    interface Props {
        curie: string;
        /**
         * Persist the new CURIE. Reject (throw) with an Error whose message
         * explains the failure (e.g. "already in use") to surface it inline;
         * the editor stays open so the value can be corrected. Resolve to
         * accept and close the editor.
         */
        save: (newCurie: string) => Promise<void>;
    }

    const { curie, save }: Props = $props();

    let editing = $state(false);
    let value = $state("");
    let error = $state<string | null>(null);
    let saving = $state(false);

    function startEdit() {
        value = curie;
        error = null;
        editing = true;
    }

    function cancel() {
        editing = false;
        error = null;
    }

    async function commit() {
        const next = value.trim();
        if (!next || next === curie) {
            cancel();
            return;
        }
        saving = true;
        error = null;
        try {
            await save(next);
            editing = false;
        } catch (e) {
            // Keep the editor open so the CURIE can be corrected.
            error = e instanceof Error ? e.message : String(e);
        } finally {
            saving = false;
        }
    }
</script>

{#if editing}
    <span class="curie-editor">
        <input
            class="curie-input"
            type="text"
            bind:value
            disabled={saving}
            {@attach (el) => {
                el.focus();
                el.select();
            }}
            onkeydown={(e) => {
                if (e.key === "Enter") commit();
                if (e.key === "Escape") cancel();
            }}
        />
        <button class="btn small muted" disabled={saving} onclick={commit}
            >{saving ? "…" : "Save"}</button
        >
        <button class="btn small muted" disabled={saving} onclick={cancel}
            >Cancel</button
        >
        {#if error}
            <p class="error">{error}</p>
        {/if}
    </span>
{:else}
    <button
        class="curie-display"
        onclick={startEdit}
        title="Click to edit CURIE"><code>{curie}</code></button
    >
{/if}

<style>
    .curie-editor {
        display: inline-flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
    }

    .curie-display {
        border: none;
        background: none;
        padding: 0;
        cursor: pointer;
        font: inherit;
        color: inherit;
    }

    .curie-display:hover code {
        text-decoration: underline;
    }

    .curie-input {
        padding: 0.15rem 0.4rem;
        border: 1px solid #aaa;
        border-radius: 3px;
        font-size: 0.8rem;
        font-family: monospace;
        box-sizing: border-box;
    }

    .error {
        width: 100%;
        color: #c00;
        font-size: 0.8rem;
        margin: 0;
    }
</style>
