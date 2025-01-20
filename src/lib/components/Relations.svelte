<script lang="ts">
    import { getContext } from "svelte";
    import { displayPredicate } from "$lib/relations.svelte.ts";
    import { isStrain } from "$lib/resources.svelte.ts";
    import type { bodyStore } from "$lib/body.svelte.ts";

    const body: bodyStore = getContext("body");
</script>

{#if body.relations.size}
    <h2>Relations</h2>

    {#each body.resources.values() as resource}
        <div class="relations-summary">
            {#if isStrain(resource)}
                {@const triples = body.relations.subset({ subject: resource })}
                {#if triples.size}
                    <div style="width: 100%; display: table;">
                        <div style="display: table-row">
                            <div class="subject">
                                {resource.name}
                            </div>

                            <div class="relations">
                                {#each triples as { subject, predicate, object }}
                                    <div class="predicate">
                                        {displayPredicate(predicate)}
                                        <span class="object">
                                            {object.name}
                                        </span>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    </div>
                {/if}
            {/if}
        </div>
    {/each}
{/if}
