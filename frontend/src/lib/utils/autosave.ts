import type { AnnotationState } from "../annotation.svelte.ts";
import { saveAnnotation } from "../api";

export interface SaveResult {
    success: boolean;
    error?: string;
}

/**
 * Saves the annotation state to the API
 */
export async function saveAnnotationState(
    state: AnnotationState,
): Promise<SaveResult> {
    try {
        const payload = {
            user: state.user,
            reference: state.reference,
            project_id: state.project_id,
            entities: state.entities.valueSeq().toArray(),
            pointers: state.pointers.valueSeq().toArray(),
            relations: state.relations.toArray().map((r) => r.toObject()),
            completed: state.completed,
        };

        const jsonString = JSON.stringify(payload);

        console.log("Saving annotation state:", payload);
        console.log("Payload JSON string:", jsonString);

        await saveAnnotation(jsonString);

        console.log("Save successful");
        return { success: true };
    } catch (error) {
        console.error("Save error:", error);
        return {
            success: false,
            error: error instanceof Error ? error.message : "Unknown error",
        };
    }
}

/**
 * Creates a debounced version of the save function
 */
export function createDebouncedSave(delayMs: number = 2000): {
    scheduleSave: (state: AnnotationState) => Promise<SaveResult>;
    cancelPending: () => void;
} {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let pendingResolve: ((result: SaveResult) => void) | null = null;

    function cancelPending() {
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        if (pendingResolve) {
            pendingResolve({
                success: false,
                error: "Save cancelled due to new changes",
            });
            pendingResolve = null;
        }
    }

    async function scheduleSave(
        state: AnnotationState,
    ): Promise<SaveResult> {
        cancelPending();

        return new Promise((resolve) => {
            pendingResolve = resolve;
            timeoutId = setTimeout(async () => {
                const result = await saveAnnotationState(state);
                if (pendingResolve === resolve) {
                    pendingResolve = null;
                    timeoutId = null;
                    resolve(result);
                }
            }, delayMs);
        });
    }

    return { scheduleSave, cancelPending };
}
