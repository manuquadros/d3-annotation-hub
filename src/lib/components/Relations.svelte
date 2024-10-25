<script lang="ts">
    import { getContext } from "svelte";
    import { displayPredicate } from "$lib/relations.svelte.ts";
    import type { bodyStore } from "$lib/body.svelte.ts";

    const body: bodyStore = getContext("body");
</script>

{#if body.relations.size}
    <h2>Relations</h2>

    {#each body.relations.predicates as predicate}
        <div class="relations-summary">
            {#each body.relations.subset({ predicate }) as { subject, object }}
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
