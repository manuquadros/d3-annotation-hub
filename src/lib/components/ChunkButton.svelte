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
    class="entity"
    type="button"
    typeof={resource.label}
    resource={key}
    on:click={handleSpanClick}
>
    {resource.name}
</button>
