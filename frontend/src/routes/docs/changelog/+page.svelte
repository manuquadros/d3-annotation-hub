<script lang="ts">
    import { html } from "virtual:changelog";
</script>

<div class="changelog">
    {@html html}
</div>

<style>
    .changelog :global(h2) {
        font-size: 1.1rem;
        font-weight: 700;
        font-family: var(--font-mono, monospace);
        border-bottom: 2px solid var(--color-border, #ddd);
        padding-bottom: 0.3rem;
        margin-top: 2.5rem;
        margin-bottom: 0.75rem;
    }

    .changelog :global(h3) {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--color-text-muted, #888);
        margin-top: 1.1rem;
        margin-bottom: 0.35rem;
    }
</style>
