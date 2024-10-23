<script lang="ts">
    import { getContext } from "svelte";
    import {
        dragStart,
        dragOver,
        handleDrop,
        handleSpanClick,
    } from "$lib/handlers";
    import type { Resource } from "$lib/resources.ts";
    import type { bodyStore } from "$lib/body";

    export let key: string;
    export let resource: Resource;

    const body: bodyStore = getContext("body");
</script>

<button
    class="entity entitySummary"
    typeof={resource.label}
    type="button"
    draggable="true"
    resource={key}
    on:dragstart={dragStart}
    on:dragover={dragOver}
    on:drop={(e) => handleDrop(e, body)}
    on:click={handleSpanClick}
>
    {resource.name}
</button>
