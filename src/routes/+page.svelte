<script lang="ts">
    import { browser } from "$app/environment";
    import { setContext, onMount } from "svelte";
    import type { PageData } from "./$types";

    import "../styles.css";
    import ChunkHeader from "$lib/components/ChunkHeader.svelte";
    import ChunkBody from "$lib/components/ChunkBody.svelte";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import { bodyStore } from "$lib/body";

    export let data: PageData;

    const { document } = data;
    let body: bodyStore | null = null;
    let header: Element;

    async function parse(doc: string): Promise<void> {
        let content: Document;
        if (browser) {
            content = new DOMParser().parseFromString(doc, "text/html");
        } else {
            const { JSDOM } = await import("jsdom");
            content = new JSDOM(doc).window.document;
        }

        header = content?.querySelector(".metadata") as Element;
        body = new bodyStore(content?.querySelector(".chunk-body") as Element);
    }

    parse(document);
    setContext("body", body);

    onMount(() => {
        body?.buttonize();
    });
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
