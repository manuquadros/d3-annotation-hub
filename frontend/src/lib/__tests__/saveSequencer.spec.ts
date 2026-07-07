import { describe, it, expect } from "vitest";
import { SaveSequencer } from "$lib/utils/saveSequencer";

describe("SaveSequencer", () => {
    it("marks the only in-flight save as current", () => {
        const seq = new SaveSequencer();
        const a = seq.begin();
        expect(a.isCurrent()).toBe(true);
        expect(a.signal.aborted).toBe(false);
    });

    it("supersedes and aborts the prior save when a newer one begins", () => {
        const seq = new SaveSequencer();
        const older = seq.begin();
        const newer = seq.begin();

        expect(older.isCurrent()).toBe(false);
        expect(older.signal.aborted).toBe(true);
        expect(newer.isCurrent()).toBe(true);
        expect(newer.signal.aborted).toBe(false);
    });

    it("keeps only the latest save current across several starts", () => {
        const seq = new SaveSequencer();
        const first = seq.begin();
        const second = seq.begin();
        const third = seq.begin();

        expect(first.isCurrent()).toBe(false);
        expect(second.isCurrent()).toBe(false);
        expect(third.isCurrent()).toBe(true);
        expect(first.signal.aborted).toBe(true);
        expect(second.signal.aborted).toBe(true);
        expect(third.signal.aborted).toBe(false);
    });

    it("hands each save an independent signal", () => {
        const seq = new SaveSequencer();
        const a = seq.begin();
        const b = seq.begin();
        expect(a.signal).not.toBe(b.signal);
    });
});
