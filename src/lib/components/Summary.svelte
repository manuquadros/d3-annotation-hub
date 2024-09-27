<script lang="ts">
    import { classes } from "$lib/resources.ts";
    import ResourceButton from "$lib/components/ResourceButton.svelte";

    function plural(singular: string): string {
        if (singular === "Bacteria") {
            return singular;
        } else {
            return singular + "s";
        }
    }
</script>

<h2>Entities</h2>

{#each $classes as [label, resources]}
    {#if resources.length}
        <h3>{plural(label.split(":")[1])}</h3>
        {#each resources as resource}
            {#if resource.count}
                <ResourceButton {resource} />
            {/if}
        {/each}
    {/if}
{/each}
