<script lang="ts">
    import "../styles.css";
    import ChunkHeader from "./ChunkHeader.svelte";
    import ChunkBody from "./ChunkBody.svelte";
    import Summary from "./Summary.svelte";
    import { onMount, SvelteComponent } from "svelte";
    import { page } from "$app/stores";
    let promise;

    const annotator = $page.url.searchParams.get("annotator");
    const id = $page.url.searchParams.get("id");

    let content: Document | null = null;
    let loading = true;
    let error: Error | null = null;
    let header: HTMLDivElement | null = null;
    let body: HTMLDivElement | null = null;

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
            body = content.querySelector(".chunk-body");
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

    onMount(() => {
        promise = loadChunk();
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
            <ChunkBody {body} />
        </div>

        <div id="summary">
            <Summary />
        </div>
    {:else}
        <p>Nothing to show here.</p>
    {/if}
</div>
