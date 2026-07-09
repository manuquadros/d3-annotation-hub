import { describe, expect, test, vi } from "vitest";
import DOMPurify from "dompurify";
import { Map } from "immutable";
import type { Map as ImmutableMap } from "immutable";
import type { Pointer } from "$lib/types.ts";
import {
    allOccurrences,
    uncoveredOffsets,
    AnnotationState,
    createRangeFromOffsets,
    buildTextNodeIndex,
} from "$lib/annotation.svelte.ts";

function makePointers(
    spans: Array<{ offset: number; length: number }>,
): ImmutableMap<string, Pointer> {
    return Map(
        spans.map((span, i) => [
            `ptr_${i}`,
            {
                entity_id: "e1",
                reference_id: 1,
                field: "body" as const,
                exact_text: "",
                prefix_text: "",
                suffix_text: "",
                ...span,
            },
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

    test("filters against many spans regardless of insertion order", () => {
        // Spans [0,3), [10,13), [20,23), supplied out of order.
        const pointers = makePointers([
            { offset: 0, length: 3 },
            { offset: 20, length: 3 },
            { offset: 10, length: 3 },
        ]);
        const candidates = [
            { offset: 5, length: 3 }, // [5,8) — gap, kept
            { offset: 12, length: 4 }, // [12,16) — overlaps [10,13), dropped
            { offset: 23, length: 2 }, // [23,25) — abuts [20,23) end, kept
        ];
        expect(uncoveredOffsets(candidates, pointers)).toEqual([
            { offset: 5, length: 3 },
            { offset: 23, length: 2 },
        ]);
    });
});

function makeState(
    pointerEntityIds: string[],
    entityIds: string[],
): AnnotationState {
    return new AnnotationState({
        user: {
            user_id: "550e8400-e29b-41d4-a716-446655440000",
            email: "test@example.com",
        },
        project_id: 1,
        reference: {
            reference_id: 1,
            pubmed_id: 1,
            pmc_id: null,
            pmc_open: null,
            doi: null,
            authors: "A",
            title: "T",
            journal: "J",
            volume: "1",
            number: null,
            pages: "1",
            year: 2020,
            body: "x".repeat(200),
        },
        entities: entityIds.map((id) => ({
            entity_id: id,
            preferred_name: id,
            kind: "Bacteria",
            synonyms: [],
            confirmed: true,
            uri: null,
        })),
        pointers: pointerEntityIds.map((entity_id, i) => ({
            entity_id,
            reference_id: 1,
            offset: i,
            length: 1,
        })),
        relations: [],
        completed: false,
    });
}

describe("createRangeFromOffsets", () => {
    function div(html: string): HTMLDivElement {
        const el = document.createElement("div");
        el.innerHTML = html;
        return el;
    }

    test("resolves an offset span within a single text node", () => {
        const el = div("Hello world foo");
        const range = createRangeFromOffsets(el, 6, 11);
        expect(range?.toString()).toBe("world");
    });

    test("resolves a span that crosses element (text-node) boundaries", () => {
        // plain text: "Hello brave world" across three text nodes.
        const el = div("Hello <b>brave</b> world");
        expect(el.textContent).toBe("Hello brave world");

        expect(createRangeFromOffsets(el, 6, 11)?.toString()).toBe("brave");
        // "lo brave wo" spans the leading node, the <b> node, and the trailing.
        expect(createRangeFromOffsets(el, 3, 14)?.toString()).toBe(
            "lo brave wo",
        );
    });

    test("a span reaching the very end of the text resolves", () => {
        const el = div("abc<i>def</i>");
        expect(createRangeFromOffsets(el, 3, 6)?.toString()).toBe("def");
    });

    test("returns null when the end offset is out of range", () => {
        const el = div("short");
        expect(createRangeFromOffsets(el, 0, 999)).toBeNull();
    });

    test("passing a prebuilt index yields the same range as without", () => {
        const el = div("Hello <b>brave</b> world");
        const index = buildTextNodeIndex(el);
        const withIndex = createRangeFromOffsets(el, 6, 11, index);
        const withoutIndex = createRangeFromOffsets(el, 6, 11);
        expect(withIndex?.toString()).toBe("brave");
        expect(withoutIndex?.toString()).toBe("brave");
    });
});

describe("AnnotationState.pointerCountByEntity", () => {
    test("counts pointers per entity id", () => {
        const state = makeState(["a", "a", "a", "b"], ["a", "b"]);
        expect(state.pointerCountByEntity.get("a")).toBe(3);
        expect(state.pointerCountByEntity.get("b")).toBe(1);
        expect(state.pointerCountByEntity.get("missing") ?? 0).toBe(0);
    });

    test("recomputes after a pointer is deleted", () => {
        const state = makeState(["a", "a", "b"], ["a", "b"]);
        expect(state.pointerCountByEntity.get("a")).toBe(2);
        state.delete("ptr_0");
        expect(state.pointerCountByEntity.get("a")).toBe(1);
    });
});

describe("AnnotationState.plainText", () => {
    test("sanitizes each field at most once and reuses the result", () => {
        const state = makeState(["a"], ["a"]);
        const spy = vi.spyOn(DOMPurify, "sanitize");
        try {
            const first = state.plainText("body");
            const second = state.plainText("body");
            expect(second).toBe(first);
            expect(spy).toHaveBeenCalledTimes(1);
        } finally {
            spy.mockRestore();
        }
    });
});

describe("AnnotationState undo history", () => {
    test("is bounded so it cannot grow without limit", () => {
        const state = makeState([], ["a"]);
        for (let i = 0; i < 150; i++) state.addSynonym("a", `syn${i}`);

        let undos = 0;
        while (state.canUndo && undos <= 200) {
            state.undo();
            undos++;
        }
        expect(undos).toBe(100);
    });
});
