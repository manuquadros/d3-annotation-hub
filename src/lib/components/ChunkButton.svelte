<script lang="ts">
    import { handleSpanClick } from "$lib/handlers";
    import { getContext, hasContext } from "svelte";
    import type { Readable } from "svelte/store";

    export let spanid: string;
    export let name: string;

    let entspans: Readable<Map<string, HTMLSpanElement>> =
        getContext("entspans");

    $: span = entspans?.get(spanid);
    $: resourceid = span?.getAttribute("resource") || "";
    $: label = span?.getAttribute("typeof") || "";
</script>

<button
    class="entity"
    type="button"
    typeof={label}
    resource={resourceid}
    on:click={handleSpanClick}
>
    {name}
</button>
