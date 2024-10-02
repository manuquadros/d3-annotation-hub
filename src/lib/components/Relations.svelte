<script lang="ts">
  import { relations, displayPredicate } from "$lib/relations.ts";
    //import ResourceButton from "$lib/components/ResourceButton.svelte";
</script>

{#if $relations.size}
    <h2>Relations</h2>

    {#each $relations as [predicate, pairs]}
        {#if pairs.size}
            {#each pairs as { subject, object }}
                <span class="relation">
                    <span class="subject">
                        {subject.name}
                    </span>
                    <span class="predicate">
                        {displayPredicate(predicate)}
                    </span>
                    <span class="object">
                        {object.name}
                    </span>
                </span>
            {/each}
        {/if}
    {/each}
{/if}
