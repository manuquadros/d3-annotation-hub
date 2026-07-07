import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { AnnotationState } from "$lib/annotation.svelte.ts";

const saveAnnotation = vi.fn();
vi.mock("$lib/api", () => ({
    saveAnnotation: (...args: unknown[]) => saveAnnotation(...args),
}));

import {
    saveAnnotationState,
    createDebouncedSave,
} from "$lib/utils/autosave.ts";

/** Minimal stand-in exposing only what the payload builder reads. */
function fakeState(): AnnotationState {
    const empty = { valueSeq: () => ({ toArray: () => [] }) };
    return {
        user: "u",
        reference: "r",
        project_id: 1,
        entities: empty,
        pointers: empty,
        relations: { toArray: () => [] },
        completed: false,
    } as unknown as AnnotationState;
}

beforeEach(() => {
    saveAnnotation.mockReset();
});

describe("saveAnnotationState", () => {
    it("returns cancelled without a network call when the signal is already aborted", async () => {
        const controller = new AbortController();
        controller.abort();

        const result = await saveAnnotationState(
            fakeState(),
            controller.signal,
        );

        expect(result).toEqual({ success: false, cancelled: true });
        expect(saveAnnotation).not.toHaveBeenCalled();
    });

    it("forwards the abort signal to saveAnnotation", async () => {
        saveAnnotation.mockResolvedValue(undefined);
        const controller = new AbortController();

        await saveAnnotationState(fakeState(), controller.signal);

        expect(saveAnnotation).toHaveBeenCalledWith(
            expect.any(String),
            controller.signal,
        );
    });

    it("reports cancelled (not an error) when the in-flight request is aborted", async () => {
        const controller = new AbortController();
        saveAnnotation.mockImplementation(() => {
            controller.abort();
            const err = new Error("aborted") as Error & { status?: number };
            return Promise.reject(err);
        });

        const result = await saveAnnotationState(
            fakeState(),
            controller.signal,
        );

        expect(result).toEqual({ success: false, cancelled: true });
    });

    it("does not retry after an abort", async () => {
        const controller = new AbortController();
        saveAnnotation.mockImplementation(() => {
            controller.abort();
            return Promise.reject(new Error("network"));
        });

        await saveAnnotationState(fakeState(), controller.signal);

        expect(saveAnnotation).toHaveBeenCalledTimes(1);
    });

    it("surfaces a permanent HTTP error", async () => {
        const err = new Error("Unprocessable") as Error & { status: number };
        err.status = 422;
        saveAnnotation.mockRejectedValue(err);

        const result = await saveAnnotationState(fakeState());

        expect(result).toEqual({ success: false, error: "Unprocessable" });
    });
});

describe("createDebouncedSave", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });
    afterEach(() => {
        vi.useRealTimers();
    });

    it("cancelPending resolves the pending save as cancelled, not as an error", async () => {
        const { scheduleSave, cancelPending } = createDebouncedSave(2000);

        const pending = scheduleSave(fakeState());
        cancelPending();

        await expect(pending).resolves.toEqual({
            success: false,
            cancelled: true,
        });
        expect(saveAnnotation).not.toHaveBeenCalled();
    });

    it("debounces rapid edits into a single save", async () => {
        saveAnnotation.mockResolvedValue(undefined);
        const { scheduleSave } = createDebouncedSave(2000);

        const p1 = scheduleSave(fakeState());
        const p2 = scheduleSave(fakeState());

        await vi.advanceTimersByTimeAsync(2000);

        await expect(p1).resolves.toEqual({ success: false, cancelled: true });
        await expect(p2).resolves.toEqual({ success: true });
        expect(saveAnnotation).toHaveBeenCalledTimes(1);
    });

    it("aborts an in-flight save when a newer one starts (no stale overwrite)", async () => {
        let firstSignal: AbortSignal | undefined;
        // The first request stays pending until its signal aborts, then rejects
        // like a real fetch() cancellation does.
        saveAnnotation
            .mockImplementationOnce((_json: string, signal: AbortSignal) => {
                firstSignal = signal;
                return new Promise((_resolve, reject) => {
                    signal.addEventListener(
                        "abort",
                        () => reject(new DOMException("aborted", "AbortError")),
                        { once: true },
                    );
                });
            })
            .mockResolvedValueOnce(undefined);

        const { scheduleSave } = createDebouncedSave(2000);

        const p1 = scheduleSave(fakeState());
        await vi.advanceTimersByTimeAsync(2000); // first save now in-flight
        expect(firstSignal?.aborted).toBe(false);

        // A newer edit arrives while the first request is still pending: it must
        // abort the older one so a stale response can never land after the newer.
        const p2 = scheduleSave(fakeState());
        expect(firstSignal?.aborted).toBe(true);

        await vi.advanceTimersByTimeAsync(2000); // second save runs

        await expect(p1).resolves.toMatchObject({ cancelled: true });
        await expect(p2).resolves.toEqual({ success: true });
        expect(saveAnnotation).toHaveBeenCalledTimes(2);
    });
});
