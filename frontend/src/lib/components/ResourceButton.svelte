<script lang="ts">
    import { getContext } from "svelte";
    import {
        dragStart,
        dragOver,
        handleDrop,
        handleSpanClick,
    } from "$lib/handlers";
    import type { Resource } from "$lib/resources.svelte.ts";
    import type { BodyStore } from "$lib/body.svelte.ts";

    interface Props {
        resource: Resource;
    }

    let { resource }: Props = $props();

    const body: BodyStore = getContext("body");
</script>

<button
    class="entity entitySummary"
    typeof={resource.label}
    type="button"
    draggable="true"
    resource={resource.resourceid}
    ondragstart={dragStart}
    ondragover={dragOver}
    ondrop={(e) => handleDrop(e, body)}
    onclick={(e) => handleSpanClick(e, body)}
>
    {resource.name}
</button>
