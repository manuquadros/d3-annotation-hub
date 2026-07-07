import type { AnnotationState } from "../annotation.svelte.ts";
import { saveAnnotation } from "../api";

export interface SaveResult {
    success: boolean;
    error?: string;
    /**
     * True when the save was superseded by a newer one (debounce cancelled or
     * in-flight request aborted). Consumers should ignore these — they are not
     * failures and must not surface as an error to the user.
     */
    cancelled?: boolean;
}

const TRANSIENT_STATUSES = new Set([502, 503, 504]);
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 3000;

/** A delay that settles early (as aborted) if the signal fires. */
function abortableDelay(ms: number, signal?: AbortSignal): Promise<void> {
    return new Promise((resolve) => {
        const timer = setTimeout(() => {
            signal?.removeEventListener("abort", onAbort);
            resolve();
        }, ms);
        function onAbort() {
            clearTimeout(timer);
            resolve();
        }
        signal?.addEventListener("abort", onAbort, { once: true });
    });
}

/**
 * Saves the annotation state to the API, retrying on transient errors
 * (network failures, 502/503/504) up to MAX_RETRIES times.
 *
 * If `signal` aborts (a newer save superseded this one), the save stops and
 * returns `{ success: false, cancelled: true }` without retrying.
 */
export async function saveAnnotationState(
    state: AnnotationState,
    signal?: AbortSignal,
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
        if (signal?.aborted) return { success: false, cancelled: true };
        try {
            await saveAnnotation(jsonString, signal);
            return { success: true };
        } catch (error) {
            if (signal?.aborted) return { success: false, cancelled: true };
            const status =
                error instanceof Object && "status" in error
                    ? (error as { status?: number }).status
                    : undefined;
            // status undefined means a network-level failure (fetch threw before
            // receiving a response) — always transient. Known HTTP error codes
            // like 401/422 are permanent and should not be retried.
            const isTransient =
                status === undefined || TRANSIENT_STATUSES.has(status);

            if (!isTransient || attempt === MAX_RETRIES) {
                console.error("Save error:", error);
                return {
                    success: false,
                    error:
                        error instanceof Error
                            ? error.message
                            : "Unknown error",
                };
            }

            console.warn(
                `Save attempt ${attempt + 1} failed (${status ?? "network error"}), retrying in ${RETRY_DELAY_MS}ms…`,
            );
            await abortableDelay(RETRY_DELAY_MS, signal);
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
    // The save currently talking to the server. Aborted when a newer save
    // starts, so an older (possibly retrying) request can never land after a
    // newer one and overwrite it with stale data.
    let inFlight: AbortController | null = null;

    function cancelPending() {
        if (timeoutId !== null) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
        if (pendingResolve) {
            pendingResolve({ success: false, cancelled: true });
            pendingResolve = null;
        }
        if (inFlight) {
            inFlight.abort();
            inFlight = null;
        }
    }

    async function scheduleSave(state: AnnotationState): Promise<SaveResult> {
        cancelPending();

        return new Promise((resolve) => {
            pendingResolve = resolve;
            timeoutId = setTimeout(() => {
                // The debounce window elapsed: this save is now committed and can
                // no longer be cancelled as "pending", so hand off from the timer
                // guard to the in-flight abort guard.
                pendingResolve = null;
                timeoutId = null;
                const controller = new AbortController();
                inFlight = controller;
                saveAnnotationState(state, controller.signal).then((result) => {
                    if (inFlight === controller) inFlight = null;
                    resolve(result);
                });
            }, delayMs);
        });
    }

    return { scheduleSave, cancelPending };
}
