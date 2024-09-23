<script lang="ts">
    import { resources } from "$lib/resources.ts";
    function plural(singular: string): string {
        if (singular === "Bacteria") {
            return singular;
        } else {
            return singular + "s";
        }
    }
</script>

<h2>Entities</h2>

{#if $entities.size > 0}
    {#each $entities.entries() as [label, resources]}
        <h3>{plural(label.slice(4))}</h3>
        {#each resources.entries() as [id, entity]}
            {#if entity.count}
                <span
                    class="entity entitySummary"
                    typeof={label}
                    property="sameAs"
                    resource={id}
                >
                    {entity.name}
                </span>
            {/if}
        {/each}
    {/each}
{/if}
