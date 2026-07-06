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
        /**
         * When true, committing an unchanged (but non-empty) value still calls
         * `save` with the current CURIE, so a caller can treat "accept as-is"
         * as a confirmation. When false (default), an unchanged value just
         * closes the editor without calling `save`.
         */
        confirmUnchanged?: boolean;
    }

    const { curie, save, confirmUnchanged = false }: Props = $props();

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
        // A rapid double-Enter can call commit() again before disabled={saving}
        // reaches the DOM; guard so the second call can't fire a duplicate save.
        if (saving) return;
        const next = value.trim();
        if (!next || (next === curie && !confirmUnchanged)) {
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
            class="form-control small curie-input"
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
            <p class="invalid-feedback curie-error">{error}</p>
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

    /* Sizing/border/focus come from `.form-control.small`; only the inline width
       and monospace CURIE face are component-specific. */
    .curie-input {
        width: auto;
        font-family: monospace;
    }

    /* Colour/typography come from `.invalid-feedback`; force it onto its own row
       within the inline-flex editor and drop the block's vertical padding. */
    .curie-error {
        flex-basis: 100%;
        padding-top: 0.2rem;
        padding-bottom: 0;
        margin: 0;
    }
</style>
