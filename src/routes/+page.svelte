<script lang="ts">
    import "../styles.css";
    import ChunkHeader from "$lib/components/ChunkHeader.svelte";
    import ChunkBody from "$lib/components/ChunkBody.svelte";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import { onMount, setContext } from "svelte";
    import { page } from "$app/stores";

    import { bodyStore } from "$lib/body.ts";
    import type { Readable } from "svelte/motion";

    const annotator = $page.url.searchParams.get("annotator");
    const id = $page.url.searchParams.get("id");

    let content: Document | null = null;
    let loading = true;
    let error: Error | null = null;
    let header: HTMLDivElement | null = null;
    let body: Readable<Element>;
    setContext("body", body);

    async function loadChunk(): Promise<void> {
        try {
            let url: string;
            if (annotator && id) {
                url = `http://localhost:8000/annotation/?annotator=${annotator}&id=${id}`;
            } else if (id) {
                console.log(`loading article ${id}`);
                url = `http://localhost:8000/segment/?pmid=${id}`;
            } else {
                console.log("start and pmid are null");
                url = "http://localhost:8000/segment/";
            }
            const response = await fetch(url);
            const data = await response.json();
            content = new DOMParser().parseFromString(
                JSON.parse(data).content,
                "text/html",
            );
            header = content.querySelector(".metadata");
        } catch (err) {
            console.error(err);
            error =
                err instanceof Error
                    ? err
                    : new Error("An unknown error occurred");
        } finally {
            loading = false;
        }
    }

    onMount(async () => {
        await loadChunk();
        body = new bodyStore(content?.querySelector(".chunk-body") as Element);
    });
</script>

<div id="container">
    {#if loading}
        <p>Loading...</p>
    {:else if error}
        <p style="color: red">{error.message}</p>
    {:else if content}
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
    {:else}
        <p>Nothing to show here.</p>
    {/if}
</div>
