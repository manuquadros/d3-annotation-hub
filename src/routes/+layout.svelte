<script>
    /**
     * @typedef {Object} Props
     * @property {import('svelte').Snippet} [children]
     */

    /** @type {Props} */
    import "../styles.css";
    let { children } = $props();
</script>

<h1>Annotation hub</h1>

<div class="layout">
    {@render children?.()}
</div>

<style>
</style>
