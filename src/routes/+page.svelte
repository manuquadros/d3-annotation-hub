<script lang="ts">
    import "../styles.css";
    import ChunkHeader from "./ChunkHeader.svelte";
    import ChunkBody from "./ChunkBody.svelte";
    import { onMount } from "svelte";
    import { page } from "$app/stores";
    let promise;

    const annotator = $page.url.searchParams.get("annotator");
    const id = $page.url.searchParams.get("id");

    let content: Document | null = null;
    let loading = true;
    let error: Error | null = null;
    let header: HTMLDivElement | null = null;
    let body: HTMLDivElement | null = null;

    let entities: { type: string; text: string; resource: string }[] = [];
    let strains: { type: string; text: string; resource: string }[] = [];
    let species: { type: string; text: string; resource: string }[] = [];
    let enzymes: { type: string; text: string; resource: string }[] = [];

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

    function handleEntityFound(event: CustomEvent) {
        const { type, text, resource } = event.detail;
        entities = [...entities, { type, text, resource }];
        strains = entities.filter((entity) => entity.type == "d3o:Strain");
        species = entities.filter((entity) => entity.type == "d3o:Bacteria");
        enzymes = entities.filter((entity) => entity.type == "d3o:Enzyme");
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
            <ChunkBody {body} on:entityFound={handleEntityFound} />
        </div>

        <div id="summary">
            <h2>Summary</h2>

            {#if entities.length > 0}
                {#if enzymes.length > 0}
                    <h3>Enzymes</h3>
                    {#each enzymes as entity}
                        <span
                            class="entitySummary"
                            typeof={entity.type}
                            property="sameAs"
                            resource={entity.resource}
                        >
                            {entity.text}
                        </span>
                    {/each}
                {/if}
                {#if strains.length > 0}
                    <h3>Strains</h3>
                    {#each strains as entity}
                        <span
                            class="entitySummary"
                            typeof={entity.type}
                            property="sameAs"
                            resource={entity.resource}
                        >
                            {entity.text}
                        </span>
                    {/each}
                {/if}

                {#if species.length > 0}
                    <h3>Bacteria</h3>
                    {#each species as entity}
                        <span
                            class="entitySummary"
                            typeof={entity.type}
                            property="sameAs"
                            resource={entity.resource}
                        >
                            {entity.text}
                        </span>
                    {/each}
                {/if}
            {:else}
                <p>No entities found.</p>
            {/if}
        </div>
    {:else}
        <p>Nothing to show here.</p>
    {/if}
</div>
