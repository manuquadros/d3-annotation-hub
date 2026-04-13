<script lang="ts">
    import { getContext } from "svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import type { Entity, Relation } from "$lib/types.ts";

    const annotationState = getContext<AnnotationState>("annotationState");

    function getEntityName(entity: Entity, entityId: string): string {
        return entity.preferred_name || `Entity ${entityId.slice(-6)}`;
    }

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
                                <span class="entity">{getEntityName(subject, rel.subject)}</span>
                                <span class="arrow">→</span>
                                <span class="entity">{getEntityName(object, rel.object)}</span>
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

    .entity {
        font-weight: 600;
        font-size: 0.9rem;
    }

    .arrow {
        color: #999;
        font-size: 0.85rem;
        flex-shrink: 0;
    }
</style>
