<script lang="ts">
    export let header: Element | null = null;
</script>

{#if header}
    <div id="header">
        {@html header.innerHTML}
    </div>
{/if}
