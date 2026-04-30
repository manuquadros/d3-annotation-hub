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
    const entitiesByKind: Map<
        string,
        Array<{ id: string; entity: Entity }>
    > = $derived.by(() => {
        const grouped = new Map<
            string,
            Array<{ id: string; entity: Entity }>
        >();

        for (const [id, entity] of annotationState.entities.entries()) {
            const kind = entity.kind;
            if (!grouped.has(kind)) {
                grouped.set(kind, []);
            }
            grouped.get(kind)!.push({ id, entity });
        }

        // Sort kinds alphabetically
        return new Map(
            [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b)),
        );
    });

    /**
     * Converts a singular entity kind to its plural form.
     * Special cases are handled explicitly, otherwise appends "s".
     */
    function plural(singular: string): string {
        // Extract the label part after the colon (e.g., "d3o:Bacteria" -> "Bacteria")
        const label = singular.includes(":")
            ? singular.split(":")[1]
            : singular;

        if (label === "Bacteria") {
            return label;
        }
        return label + "s";
    }
</script>

{#if entitiesByKind.size > 0}
    <h2>Entities</h2>

    <div class="summary-groups">
        {#each entitiesByKind.entries() as [kind, entities] (kind)}
            <div class="summary-group">
                <div class="summary-label">{plural(kind)}</div>
                <div class="entity-group">
                    {#each entities as { id } (id)}
                        <EntityButton entityId={id} />
                    {/each}
                </div>
            </div>
        {/each}
    </div>
{/if}

<style>
    @import "./summary.css";

    h2 {
        margin-top: 0;
        margin-bottom: 0.5rem;
        line-height: normal;
    }

    .entity-group {
        display: flex;
        flex-wrap: wrap;
        gap: 0.25rem;
    }
</style>
