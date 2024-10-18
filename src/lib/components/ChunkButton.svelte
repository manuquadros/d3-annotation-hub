<script lang="ts">
    import { handleSpanClick } from "$lib/handlers";
    import type { Resource } from "$lib/resources.ts";

    export let key: string;
    export let label: string;
    export let name: string;
</script>

<button
    class="entity"
    type="button"
    typeof={label}
    resource={key}
    on:click={handleSpanClick}
>
    {name}
</button>
