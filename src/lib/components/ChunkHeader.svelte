<script lang="ts">
    export let header: Document | null = null;
</script>

{#if header}
    <div id="header">
        {@html header.innerHTML}
    </div>
{/if}
