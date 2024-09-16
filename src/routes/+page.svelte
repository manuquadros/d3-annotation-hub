<script lang="ts">
    import "../styles.css";
    import Chunk from "./Chunk.svelte";
    import { page } from "$app/stores";

    const annotator = $page.url.searchParams.get("annotator");
    const id = $page.url.searchParams.get("id");

    let entities: { type: string; text: string; resource: string }[] = [];
    let strains: { type: string; text: string; resource: string }[] = [];
    let species: { type: string; text: string; resource: string }[] = [];
    let enzymes: { type: string; text: string; resource: string }[] = [];

    function handleEntityFound(event: CustomEvent) {
        const { type, text, resource } = event.detail;
        entities = [...entities, { type, text, resource }];
        strains = entities.filter((entity) => entity.type == "d3o:Strain");
        species = entities.filter((entity) => entity.type == "d3o:Bacteria");
        enzymes = entities.filter((entity) => entity.type == "d3o:Enzyme");
    }
</script>

<div id="container">
    <div id="chunk">
        <Chunk {annotator} {id} on:entityFound={handleEntityFound} />
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
</div>
