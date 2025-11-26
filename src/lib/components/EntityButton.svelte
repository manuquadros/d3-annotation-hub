<script lang="ts">
    import { getContext } from "svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import { getLabelColor, getContrastColor } from "$lib/utils.ts";

    interface Props {
        entityId: string;
    }

    const { entityId }: Props = $props();
    const annotationState = getContext<AnnotationState>("annotationState");

    /**
     * Gets the entity from the annotation state.
     */
    const entity = $derived(annotationState.entity(entityId));

    /**
     * Gets all pointers that reference this entity.
     */
    const entityPointers = $derived.by(() => {
        return annotationState.pointers
            .valueSeq()
            .filter((pointer) => pointer.entity_id === entityId)
            .toArray();
    });

    /**
     * Gets a display name for the entity.
     * Prefers designations if available, otherwise uses text from the first pointer.
     */
    const displayName = $derived.by(() => {
        if (!entity) return "";

        // If designations exist, use the first one
        if (entity.designations && entity.designations.size > 0) {
            return entity.designations.first() || "";
        }

        // Otherwise, try to get text from the first pointer (only in browser)
        if (typeof document !== "undefined" && entityPointers.length > 0) {
            const firstPointer = entityPointers[0];
            const body = annotationState.reference.body;
            if (body) {
                // Extract the text at the pointer's offset
                const tempDiv = document.createElement("div");
                tempDiv.innerHTML = body;
                const plainText = tempDiv.textContent || "";
                return plainText.slice(
                    firstPointer.offset,
                    firstPointer.offset + firstPointer.length,
                );
            }
        }

        return `Entity ${entityId.slice(-6)}`;
    });

    const labelColor = $derived(getLabelColor(entity?.kind || ""));
    const textColor = $derived(getContrastColor(labelColor));

    /**
     * Scrolls to and highlights the first annotation for this entity.
     */
    function handleClick() {
        if (entityPointers.length === 0) return;

        const firstPointer = entityPointers[0];
        const annotationElement = document.querySelector(
            `[id="${firstPointer.pointer_id}"]`,
        );

        if (annotationElement) {
            annotationElement.scrollIntoView({
                behavior: "smooth",
                block: "center",
            });

            // Add a temporary highlight effect
            annotationElement.classList.add("highlight-pulse");
            setTimeout(() => {
                annotationElement.classList.remove("highlight-pulse");
            }, 2000);
        }
    }
</script>

<button
    class="entity-button"
    style:background-color={labelColor}
    style:color={textColor}
    onclick={handleClick}
    aria-label={`View ${displayName} annotations`}
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
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.6;
            transform: scale(1.02);
        }
    }
</style>
