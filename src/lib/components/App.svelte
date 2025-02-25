<script lang="ts">
    import { setContext } from "svelte";
    import ChunkHeader from "$lib/components/ChunkHeader.svelte";
    import ChunkBody from "$lib/components/ChunkBody.svelte";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import type { BodyStore } from "$lib/body.svelte.ts";

    interface Props {
        header: Element;
        body: BodyStore;
    }

    let { header, body }: Props = $props();

    setContext("body", body);
</script>

<div id="container">
    <div id="chunk">
        <ChunkHeader {header} />
        <ChunkBody />
    </div>

    <div id="summary">
        <Summary />
    </div>

    <div id="relations">
        <Relations />
    </div>
</div>
