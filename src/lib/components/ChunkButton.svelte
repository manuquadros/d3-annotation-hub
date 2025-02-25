<script lang="ts">
    import type { BodyStore } from "$lib/body.svelte.ts";
    import { handleSpanClick } from "$lib/handlers";
    import { getContext } from "svelte";

    interface Props {
        spanid: string;
        name: string;
    }

    let { spanid, name }: Props = $props();

    let body: BodyStore = getContext("body");

    let span = $derived(body.entspans?.get(spanid));
    let resourceid = $derived(span?.getAttribute("resource") || "");
    let label = $derived(span?.getAttribute("typeof") || "");
</script>

<button
    class="entity"
    type="button"
    typeof={label}
    resource={resourceid}
    onclick={(ev) => handleSpanClick(ev, body)}
>
    {name}
</button>
