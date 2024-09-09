<script lang="ts">
    import "../styles.css";
    import Chunk from "./Chunk.svelte";
    import { page } from "$app/stores";

    const annotator = $page.url.searchParams.get("annotator");
    const id = $page.url.searchParams.get("id");

    let entities: { type: string; text: string }[] = [];
    let strains: { type: string; text: string }[] = [];
    let species: { type: string; text: string }[] = [];

    function handleEntityFound(event: CustomEvent) {
        const { type, text } = event.detail;
        entities = [...entities, { type, text }];
        strains = entities.filter(
            (entity) => entity.type == "ncbitaxon:Strain",
        );
        species = entities.filter(
            (entity) => entity.type == "ncbitaxon:Species",
        );
    }
</script>

<div id="container">
    <div id="chunk">
        <Chunk {annotator} {id} on:entityFound={handleEntityFound} />
    </div>

    <div id="summary">
        <h2>Summary</h2>

        {#if entities.length > 0}
            {#if strains.length > 0}
                <h3>Strains</h3>
                {#each strains as entity}
                    <span class="entitySummary" typeof={entity.type}>
                        {entity.text}
                    </span>
                {/each}
            {/if}

            {#if species.length > 0}
                <h3>Species</h3>
                {#each species as entity}
                    <span class="entitySummary" typeof={entity.type}>
                        {entity.text}
                    </span>
                {/each}
            {/if}
        {:else}
            <p>No entities found.</p>
        {/if}
    </div>
</div>
