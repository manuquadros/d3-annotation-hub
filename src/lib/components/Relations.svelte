<script lang="ts">
    import { relations, displayPredicate } from "$lib/relations.ts";
</script>

{#if $relations.size}
    <h2>Relations</h2>

    {#each $relations as [predicate, pairs]}
        {#if pairs.size}
            <div class="relations-summary">
                {#each pairs as { subject, object }}
                    <div class="relation">
                        <span class="subject">
                            {subject.name}
                        </span>
                        <span class="predicate">
                            {displayPredicate(predicate)}
                        </span>
                        <span class="object">
                            {object.name}
                        </span>
                    </div>
                {/each}
            </div>
        {/if}
    {/each}
{/if}
