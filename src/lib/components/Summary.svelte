<script lang="ts">
    import { classes, resources } from "$lib/resources.ts";
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

{#each $classes as [label, ids]}
    {#if ids.length}
        <h3>{plural(label.split(":")[1])}</h3>
        {#each ids as id}
            {#if $resources.get(id).count}
                <ResourceButton key={id} resource={$resources.get(id)} />
            {/if}
        {/each}
    {/if}
{/each}
