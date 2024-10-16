<script lang="ts">
    import { handleSpanClick } from "$lib/handlers";
    import type { Resource } from "$lib/resources.ts";

    export let key: string;
    export let resource: Resource;
    export let name: string;
</script>

<button
    class="entity"
    type="button"
    typeof={resource.label}
    resource={key}
    on:click={handleSpanClick}
>
    {name}
</button>
