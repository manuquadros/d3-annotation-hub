<script lang="ts">
    import { getContext } from "svelte";
    import ResourceButton from "$lib/components/ResourceButton.svelte";

    function plural(singular: string): string {
        if (singular === "Bacteria") {
            return singular;
        } else {
            return singular + "s";
        }
    }

    const body = getContext("body");
    const resources = body.resources;
    const classes = body.classes;
</script>

{#if classes.size}
    <h2>Entities</h2>

    {#each classes as label}
        <h4>{plural(label.split(":")[1])}</h4>
        {#each $resources.entries() as [key, resource]}
            {#if resource.label === label}
                <ResourceButton {key} {resource} />
            {/if}
        {/each}
    {/each}
{/if}
