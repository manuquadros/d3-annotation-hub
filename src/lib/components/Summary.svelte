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

{#if $classes.size}
    <h2>Entities</h2>

    {#each $classes as [label, ids]}
        {#if ids.length}
            <h3>{plural(label.split(":")[1])}</h3>
            {#each ids as id}
                {@const res = $resources.get(id)}
                {#if res}
                    <ResourceButton key={id} resource={res} />
                {/if}
            {/each}
        {/if}
    {/each}
{/if}
