<script lang="ts">
    import {
        dragStart,
        dragOver,
        handleDrop,
        handleSpanClick,
    } from "$lib/handlers";
    import type { Resource } from "$lib/resources.ts";

    export let key: string;
    export let resource: Resource;
</script>

<button
    class="entity entitySummary"
    typeof={resource.label}
    type="button"
    draggable="true"
    resource={key}
    on:dragstart={dragStart}
    on:dragover={dragOver}
    on:drop={handleDrop}
    on:click={handleSpanClick}
>
    {resource.name}
</button>
