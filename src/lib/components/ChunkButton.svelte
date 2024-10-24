<script lang="ts">
    import { handleSpanClick } from "$lib/handlers";
    import { getContext, hasContext } from "svelte";
    import type { Readable } from "svelte/store";

    interface Props {
        spanid: string;
        name: string;
    }

    let { spanid, name }: Props = $props();

    let entspans: Readable<Map<string, HTMLSpanElement>> =
        getContext("entspans");

    let span = $derived(entspans?.get(spanid));
    let resourceid = $derived(span?.getAttribute("resource") || "");
    let label = $derived(span?.getAttribute("typeof") || "");
</script>

<button
    class="entity"
    type="button"
    typeof={label}
    resource={resourceid}
    onclick={handleSpanClick}
>
    {name}
</button>
