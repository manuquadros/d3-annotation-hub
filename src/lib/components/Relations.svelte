<script lang="ts">
    import { getContext } from "svelte";
    import { displayPredicate } from "$lib/relations.svelte.ts";
    import {
        bacteriaLabel,
        Resource,
        strainLabel,
    } from "$lib/resources.svelte.ts";
    import type { bodyStore } from "$lib/body.svelte.ts";

    const body: bodyStore = getContext("body");
    let bodyByClass = $derived.by(() => {
        const resMap = new Map<string, Resource[]>();

        body.resources.forEach((res) => {
            resMap.get(res.label)?.push(res) || resMap.set(res.label, [res]);
        });

        return resMap;
    });
</script>

{#if body.relations.size}
    <h2>Relations</h2>

    {#if bodyByClass.size}
        <div class="relations-summary">
            {#each [strainLabel, bacteriaLabel] as entClass}
                {#each bodyByClass.get(entClass) || [] as entity}
                    {@const triples = body.relations.subset({
                        subject: entity,
                    })}
                    {#if triples.size}
                        <div style="width: 100%; display: table;">
                            <div class="subject">
                                {entity.name}
                            </div>

                            <div class="relations">
                                {#each triples as { predicate, object }}
                                    <div class="predicate">
                                        {displayPredicate(predicate)}
                                        <span class="object">
                                            {object.name}
                                        </span>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}
                {/each}
            {/each}
        </div>
    {/if}
{/if}
