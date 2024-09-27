<script lang="ts">
    import { dragStart, dragOver, handleDrop } from "$lib/handlers";
    import type { Resource } from "$lib/resources.ts";

    export let resource: Resource;
</script>

<button
    class="entity entitySummary"
    typeof={resource.label}
    type="button"
    draggable="true"
    on:dragstart={dragStart}
    on:dragover={dragOver}
    on:drop={handleDrop}
>
    {resource.name}
</button>
