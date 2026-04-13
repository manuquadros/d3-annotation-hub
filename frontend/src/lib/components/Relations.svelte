<script lang="ts">
    import { getContext } from "svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import type { Relation } from "$lib/types.ts";
    import EntityButton from "$lib/components/EntityButton.svelte";

    const annotationState = getContext<AnnotationState>("annotationState");

    function displayPredicate(predicate: string): string {
        const local = predicate.includes(":")
            ? predicate.slice(predicate.lastIndexOf(":") + 1)
            : predicate;
        return local
            .replace(/([A-Z])/g, " $1")
            .replace(/[-_]/g, " ")
            .toLowerCase()
            .trim();
    }

    /** Group all relations by predicate, preserving insertion order of predicates. */
    const byPredicate = $derived.by(() => {
        const map = new Map<string, Relation[]>();
        for (const relation of annotationState.relations.toArray()) {
            const bucket = map.get(relation.predicate);
            if (bucket) {
                bucket.push(relation);
            } else {
                map.set(relation.predicate, [relation]);
            }
        }
        return map;
    });
</script>

{#if annotationState.relations.size > 0}
    <h2>Relations</h2>

    <div class="summary-groups">
        {#each byPredicate.entries() as [predicate, relations] (predicate)}
            <div class="summary-group">
                <div class="summary-label">{displayPredicate(predicate)}</div>
                <ul class="triple-list">
                    {#each relations as rel (rel.subject + rel.object)}
                        {@const subject = annotationState.entity(rel.subject)}
                        {@const object = annotationState.entity(rel.object)}
                        {#if subject && object}
                            <li class="triple">
                                <EntityButton entityId={rel.subject} />
                                <span class="arrow">→</span>
                                <EntityButton entityId={rel.object} />
                                <button
                                    class="delete-btn"
                                    onclick={() => annotationState.removeRelation(rel)}
                                    aria-label="Delete relation"
                                >×</button>
                            </li>
                        {/if}
                    {/each}
                </ul>
            </div>
        {/each}
    </div>
{/if}


<style>
    @import '../summary.css';

    h2 {
        margin-top: 0;
        margin-bottom: 0.5rem;
        line-height: normal;
    }

    .triple-list {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }

    .triple {
        display: flex;
        align-items: baseline;
        gap: 0.4rem;
        flex-wrap: wrap;
    }

    .arrow {
        color: #999;
        font-size: 0.85rem;
        flex-shrink: 0;
    }

    .delete-btn {
        margin-left: auto;
        background: none;
        border: none;
        padding: 0 0.1rem;
        color: #bbb;
        font-size: 1rem;
        line-height: 1;
        cursor: pointer;
        flex-shrink: 0;
    }

    .delete-btn:hover {
        color: #e55;
    }
</style>
