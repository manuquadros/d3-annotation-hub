<script lang="ts">
    import { getContext } from "svelte";
    import { Set } from "immutable";
    import { AnnotationState } from "$lib/annotation.svelte";
    import { getLabelColor, getContrastColor } from "$lib/utils.ts";
    import { createRelation } from "$lib/types.ts";
    import type { EditorState } from "$lib/types.ts";

    interface Props {
        entityId: string;
    }

    const { entityId }: Props = $props();
    const annotationState = getContext<AnnotationState>("annotationState");
    const editorStateCtx = getContext<{ value: EditorState }>("editorState");

    const entity = $derived(annotationState.entity(entityId));

    const entityPointers = $derived(
        annotationState.pointers
            .entrySeq()
            .filter(([, p]) => p.entity_id === entityId)
            .toArray(),
    );

    const displayName = $derived(entity?.preferred_name ?? "");
    const labelColor = $derived(getLabelColor(entity?.kind || ""));
    const textColor = $derived(getContrastColor(labelColor));

    function openEditor() {
        editorStateCtx.value = { mode: 'edit-entity', entityId };
    }

    function handleDragStart(event: DragEvent) {
        if (event.dataTransfer) {
            event.dataTransfer.setData("text/plain", entityId);
            event.dataTransfer.effectAllowed = "link";
        }
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault();
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "link";
        }
    }

    function guessPredicate(sourceKind: string, targetKind: string): string | null {
        const isStrain = (k: string) => k === "d3o:Strain";
        const isBacteria = (k: string) => k === "d3o:Bacteria";
        const isEnzyme = (k: string) => k === "d3o:Enzyme";
        const isOrganism = (k: string) => isBacteria(k) || isStrain(k);

        if (isStrain(sourceKind) && isBacteria(targetKind)) return "d3o:hasSpecies";
        if (isEnzyme(sourceKind) && isOrganism(targetKind)) return "d3o:hasEnzyme";
        if (isOrganism(sourceKind) && isEnzyme(targetKind)) return "d3o:hasEnzyme";
        return null;
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault();
        const sourceEntityId = event.dataTransfer?.getData("text/plain");
        if (!sourceEntityId || sourceEntityId === entityId) return;

        const sourceEntity = annotationState.entity(sourceEntityId);
        const targetEntity = entity;
        if (!sourceEntity || !targetEntity) return;

        const sourceKind = sourceEntity.kind;
        const targetKind = targetEntity.kind;

        if (sourceKind === targetKind) {
            // Merge: union synonyms, re-point all pointers, remove source
            const mergedSynonyms = (sourceEntity.synonyms || Set<string>()).union(
                targetEntity.synonyms || Set<string>(),
            );
            annotationState.entities = annotationState.entities.set(entityId, {
                ...targetEntity,
                synonyms: mergedSynonyms,
            });

            let updatedPointers = annotationState.pointers;
            annotationState.pointers.forEach((pointer, key) => {
                if (pointer.entity_id === sourceEntityId) {
                    updatedPointers = updatedPointers.set(key, { ...pointer, entity_id: entityId });
                }
            });
            annotationState.pointers = updatedPointers;

            let updatedRelations = annotationState.relations;
            annotationState.relations.forEach((relation) => {
                if (relation.subject === sourceEntityId || relation.object === sourceEntityId) {
                    updatedRelations = updatedRelations.delete(relation);
                    updatedRelations = updatedRelations.add(
                        createRelation({
                            subject: relation.subject === sourceEntityId ? entityId : relation.subject,
                            predicate: relation.predicate,
                            object: relation.object === sourceEntityId ? entityId : relation.object,
                        }),
                    );
                }
            });
            annotationState.relations = updatedRelations;
            annotationState.entities = annotationState.entities.delete(sourceEntityId);
            return;
        }

        let subject: string;
        let object: string;
        let predicate: string | null;

        if (sourceKind === "d3o:Bacteria" && targetKind === "d3o:Strain") {
            subject = entityId; object = sourceEntityId; predicate = "d3o:hasSpecies";
        } else if (sourceKind === "d3o:Enzyme" && targetKind === "d3o:Strain") {
            subject = entityId; object = sourceEntityId; predicate = "d3o:hasEnzyme";
        } else if (sourceKind === "d3o:Enzyme" && targetKind === "d3o:Bacteria") {
            subject = entityId; object = sourceEntityId; predicate = "d3o:hasEnzyme";
        } else {
            subject = sourceEntityId; object = entityId;
            predicate = guessPredicate(sourceKind, targetKind);
        }

        if (predicate) {
            annotationState.relations = annotationState.relations.add(
                createRelation({ subject, predicate, object }),
            );
        }
    }
</script>

<button
    class="entity-button"
    style:background-color={labelColor}
    style:color={textColor}
    onclick={openEditor}
    draggable="true"
    ondragstart={handleDragStart}
    ondragover={handleDragOver}
    ondrop={handleDrop}
    aria-label={`Edit ${displayName}`}
>
    {displayName}
    <span class="entity-count">{entityPointers.length}</span>
</button>

<style>
    .entity-button {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 0.75rem;
        margin: 0.25rem;
        border: none;
        border-radius: 4px;
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
    }

    .entity-button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }

    .entity-button:active {
        transform: translateY(0);
    }

    .entity-count {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 1.25rem;
        height: 1.25rem;
        padding: 0 0.25rem;
        background-color: rgba(0, 0, 0, 0.15);
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    :global(.highlight-pulse) {
        animation: pulse 2s ease-in-out;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; transform: scale(1.02); }
    }
</style>
