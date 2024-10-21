<script lang="ts">
    import { getContext } from "svelte";
    import { displayPredicate } from "$lib/relations.ts";
    import type { bodyStore } from "$lib/body";

    const body: bodyStore = getContext("body");
    const relations = body.relations;
</script>

{#if $relations.size}
    <h2>Relations</h2>

    {#each relations.predicates as predicate}
        <div class="relations-summary">
            {#each relations.subset({ predicate }) as { subject, object }}
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
    {/each}
{/if}
