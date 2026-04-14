import type { AnnotationState } from "../annotation.svelte.ts";
import { saveAnnotation } from "../api";

export interface SaveResult {
    success: boolean;
    error?: string;
}

const TRANSIENT_STATUSES = new Set([502, 503, 504]);
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 3000;

/**
 * Saves the annotation state to the API, retrying on transient errors
 * (network failures, 502/503/504) up to MAX_RETRIES times.
 */
export async function saveAnnotationState(
    state: AnnotationState,
): Promise<SaveResult> {
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

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        try {
            await saveAnnotation(jsonString);
            return { success: true };
        } catch (error) {
            const status = (error as any).status as number | undefined;
            // status undefined means a network-level failure (fetch threw before
            // receiving a response) — always transient. Known HTTP error codes
            // like 401/422 are permanent and should not be retried.
            const isTransient = status === undefined || TRANSIENT_STATUSES.has(status);

            if (!isTransient || attempt === MAX_RETRIES) {
                console.error("Save error:", error);
                return {
                    success: false,
                    error: error instanceof Error ? error.message : "Unknown error",
                };
            }

            console.warn(`Save attempt ${attempt + 1} failed (${status ?? "network error"}), retrying in ${RETRY_DELAY_MS}ms…`);
            await new Promise((r) => setTimeout(r, RETRY_DELAY_MS));
        }
    }

    // unreachable
    return { success: false, error: "Max retries exceeded" };
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
