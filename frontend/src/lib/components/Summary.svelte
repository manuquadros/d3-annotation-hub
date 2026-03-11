<script lang="ts">
    import { getContext } from "svelte";
    import EntityButton from "$lib/components/EntityButton.svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import type { Entity } from "$lib/types.ts";

    const annotationState = getContext<AnnotationState>("annotationState");

    /**
     * Groups entities by their kind and returns a Map of kind -> entities array.
     * The kinds are sorted alphabetically.
     */
    const entitiesByKind = $derived.by(() => {
        const grouped = new Map<string, Array<{ id: string; entity: Entity }>>();

        for (const [id, entity] of annotationState.entities.entries()) {
            const kind = entity.kind;
            if (!grouped.has(kind)) {
                grouped.set(kind, []);
            }
            grouped.get(kind)!.push({ id, entity });
        }

        // Sort kinds alphabetically
        return new Map([...grouped.entries()].sort(([a], [b]) => a.localeCompare(b)));
    });

    /**
     * Converts a singular entity kind to its plural form.
     * Special cases are handled explicitly, otherwise appends "s".
     */
    function plural(singular: string): string {
        // Extract the label part after the colon (e.g., "d3o:Bacteria" -> "Bacteria")
        const label = singular.includes(":") ? singular.split(":")[1] : singular;

        if (label === "Bacteria") {
            return label;
        }
        return label + "s";
    }
</script>

{#if entitiesByKind.size > 0}
    <h2>Entities</h2>

    {#each entitiesByKind.entries() as [kind, entities]}
        <h4 class="summary-header">{plural(kind)}</h4>
        <div class="entity-group">
            {#each entities as { id, entity }}
                <EntityButton entityId={id} />
            {/each}
        </div>
    {/each}
{/if}

<style>
    h2, h4 {
        line-height: normal;
    }

    .entity-group {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
        margin-bottom: 1rem;
    }

    .entity-group:last-child {
        margin-bottom: 0;
        line-height: normal;
    }
</style>
