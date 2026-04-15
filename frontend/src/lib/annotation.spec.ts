import { describe, expect, test } from "vitest";
import { Map } from "immutable";
import type { Map as ImmutableMap } from "immutable";
import type { Pointer } from "$lib/types.ts";
import { allOccurrences, uncoveredOffsets } from "$lib/annotation.svelte.ts";

function makePointers(
    spans: Array<{ offset: number; length: number }>,
): ImmutableMap<string, Pointer> {
    return Map(
        spans.map((span, i) => [
            `ptr_${i}`,
            { entity_id: "e1", reference_id: 1, ...span },
        ]),
    );
}

describe("allOccurrences", () => {
    test("returns empty array for empty searchText", () => {
        expect(allOccurrences("hello world", "")).toEqual([]);
    });

    test("returns empty array when searchText is not found", () => {
        expect(allOccurrences("hello world", "xyz")).toEqual([]);
    });

    test("finds a single occurrence", () => {
        expect(allOccurrences("hello world", "world")).toEqual([
            { offset: 6, length: 5 },
        ]);
    });

    test("finds multiple non-overlapping occurrences", () => {
        expect(allOccurrences("abcabc", "abc")).toEqual([
            { offset: 0, length: 3 },
            { offset: 3, length: 3 },
        ]);
    });

    test("does not double-count overlapping matches", () => {
        // "aa" appears at 0 and 1 in "aaa", but non-overlapping search
        // advances past the first match, so only offset 0 is found.
        expect(allOccurrences("aaa", "aa")).toEqual([{ offset: 0, length: 2 }]);
    });
});

describe("uncoveredOffsets", () => {
    test("returns all candidates when there are no existing pointers", () => {
        const candidates = [
            { offset: 0, length: 5 },
            { offset: 10, length: 3 },
        ];
        expect(uncoveredOffsets(candidates, Map())).toEqual(candidates);
    });

    test("filters out a candidate exactly matched by an existing pointer", () => {
        const candidates = [{ offset: 5, length: 4 }];
        const pointers = makePointers([{ offset: 5, length: 4 }]);
        expect(uncoveredOffsets(candidates, pointers)).toEqual([]);
    });

    test("filters out a candidate partially overlapped by an existing pointer", () => {
        const candidates = [{ offset: 5, length: 4 }]; // spans 5–8
        const pointers = makePointers([{ offset: 7, length: 4 }]); // spans 7–10
        expect(uncoveredOffsets(candidates, pointers)).toEqual([]);
    });

    test("keeps candidates that are adjacent but not overlapping", () => {
        const candidates = [{ offset: 0, length: 5 }]; // spans 0–4
        const pointers = makePointers([{ offset: 5, length: 3 }]); // starts at 5
        expect(uncoveredOffsets(candidates, pointers)).toEqual(candidates);
    });

    test("returns only uncovered candidates when mix of covered and uncovered", () => {
        const covered = { offset: 5, length: 4 };
        const uncovered = { offset: 20, length: 3 };
        const pointers = makePointers([{ offset: 5, length: 4 }]);
        expect(uncoveredOffsets([covered, uncovered], pointers)).toEqual([
            uncovered,
        ]);
    });
});
