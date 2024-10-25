<script lang="ts">
    import { getContext } from "svelte";
    import {
        dragStart,
        dragOver,
        handleDrop,
        handleSpanClick,
    } from "$lib/handlers";
    import type { Resource } from "$lib/resources.svelte.ts";
    import type { bodyStore } from "$lib/body.svelte.ts";

    interface Props {
        key: string;
        resource: Resource;
    }

    let { key, resource }: Props = $props();

    const body: bodyStore = getContext("body");
</script>

<button
    class="entity entitySummary"
    typeof={resource.label}
    type="button"
    draggable="true"
    resource={key}
    ondragstart={dragStart}
    ondragover={dragOver}
    ondrop={(e) => handleDrop(e, body)}
    onclick={(e) => handleSpanClick(e, body)}
>
    {resource.name}
</button>
