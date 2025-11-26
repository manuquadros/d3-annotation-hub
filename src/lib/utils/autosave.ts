import type { AnnotationState } from "../annotation.svelte.ts";

export interface SaveResult {
    success: boolean;
    error?: string;
}

/**
 * Saves the annotation state to the API
 */
export async function saveAnnotationState(
    state: AnnotationState,
    apiUrl: string = "http://localhost:8000",
): Promise<SaveResult> {
    try {
        const payload = {
            user: state.user,
            reference: state.reference,
            entities: Object.fromEntries(state.entities.entries()),
            pointers: Object.fromEntries(state.pointers.entries()),
            relations: state.relations.toArray(),
        };

        const jsonString = JSON.stringify(payload);

        console.log("Saving annotation state:", payload);
        console.log("Payload JSON string:", jsonString);

        const response = await fetch(`${apiUrl}/save/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ json_data: jsonString }),
        });

        if (!response.ok) {
            let errorText = await response.text();
            try {
                const errorJson = JSON.parse(errorText);
                console.error("Save failed:", response.status, errorJson);
                errorText = JSON.stringify(errorJson, null, 2);
            } catch {
                console.error("Save failed:", response.status, errorText);
            }
            return {
                success: false,
                error: `Server error: ${response.status} - ${errorText}`,
            };
        }

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
    scheduleSave: (
        state: AnnotationState,
        apiUrl?: string,
    ) => Promise<SaveResult>;
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
        apiUrl?: string,
    ): Promise<SaveResult> {
        cancelPending();

        return new Promise((resolve) => {
            pendingResolve = resolve;
            timeoutId = setTimeout(async () => {
                const result = await saveAnnotationState(state, apiUrl);
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
