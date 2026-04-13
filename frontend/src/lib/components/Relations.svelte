<script lang="ts">
    import { getContext } from "svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import type { Entity, Relation } from "$lib/types.ts";

    const annotationState = getContext<AnnotationState>("annotationState");

    /**
     * Reactively computes relations for each entity.
     * Maps entity ID -> array of relations where that entity is the subject.
     */
    const relationsMap = $derived.by(() => {
        const map = new Map<string, Relation[]>();
        for (const [entityId] of annotationState.entities.entries()) {
            const entityRelations = annotationState.relations
                .filter((rel) => rel.subject === entityId)
                .toArray();
            if (entityRelations.length > 0) {
                map.set(entityId, entityRelations);
            }
        }
        return map;
    });

    /**
     * Gets display name for an entity.
     * Prefers designations if available, otherwise extracts text from the first pointer.
     */
    function getEntityName(entity: Entity, entityId: string): string {
        return entity.preferred_name || `Entity ${entityId.slice(-6)}`;
    }

    /**
     * Returns a human-readable predicate string.
     */
    function displayPredicate(predicate: string): string {
        // Strip any namespace prefix and convert camelCase/kebab-case to words
        const local = predicate.includes(":")
            ? predicate.slice(predicate.lastIndexOf(":") + 1)
            : predicate;
        return local
            .replace(/([A-Z])/g, " $1")
            .replace(/[-_]/g, " ")
            .toLowerCase()
            .trim();
    }

    /** All entity IDs that appear as subjects in at least one relation, preserving
     *  insertion order so the list is stable. */
    const subjectIds = $derived(
        [...relationsMap.keys()],
    );
</script>

{#if annotationState.relations.size > 0}
    <h2>Relations</h2>

    <div class="relations-summary">
        {#each subjectIds as entityId (entityId)}
            {@const entity = annotationState.entity(entityId)}
            {@const relations = relationsMap.get(entityId) ?? []}
            {#if entity}
                <div class="relation-row">
                    <div class="subject">{getEntityName(entity, entityId)}</div>
                    <div class="relations">
                        {#each relations as relation (relation.subject + relation.predicate + relation.object)}
                            {@const objectEntity = annotationState.entity(relation.object)}
                            {#if objectEntity}
                                <div class="predicate">
                                    {displayPredicate(relation.predicate)}
                                    <span class="object">
                                        {getEntityName(objectEntity, relation.object)}
                                    </span>
                                </div>
                            {/if}
                        {/each}
                    </div>
                </div>
            {/if}
        {/each}
    </div>
{/if}

<style>
    h2 {
        margin-top: 0;
        line-height: normal;
    }

    .relation-row {
        width: 100%;
        display: flex;
        flex-wrap: wrap;
        align-items: baseline;
        margin-bottom: 0.5em;
    }

    .relation-row .subject {
        font-weight: bold;
        white-space: nowrap;
        padding-right: 1em;
        flex-shrink: 0;
        line-height: normal;
    }

    .relation-row .relations {
        line-height: normal;
        flex-grow: 1;
    }

    .predicate {
        display: block;
        margin: 0;
    }

    .predicate:first-child {
        margin-top: 0;
    }

    .object {
        font-weight: bold;
        padding-left: 0.5em;
    }
</style>
