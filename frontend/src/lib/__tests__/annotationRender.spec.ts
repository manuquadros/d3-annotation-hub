import { describe, expect, test, vi, beforeEach } from "vitest";
import { Map } from "immutable";
import type { Map as ImmutableMap } from "immutable";
import { Set } from "immutable";
import type { Entity, Pointer } from "$lib/types.ts";

// annotateHTMLString mounts a ResourceCard per pointer; here we intercept
// svelte's mount/unmount to assert the leak fix (TICKET-23): every mounted card
// must be unmounted by the cleanup the function returns, so instances don't
// accumulate across re-renders.
const { mountMock, unmountMock } = vi.hoisted(() => ({
    mountMock: vi.fn(),
    unmountMock: vi.fn(),
}));

vi.mock("svelte", async (importOriginal) => {
    const actual = await importOriginal<typeof import("svelte")>();
    return { ...actual, mount: mountMock, unmount: unmountMock };
});

import { annotateHTMLString } from "$lib/annotation.svelte.ts";

function pointer(overrides: Partial<Pointer>): Pointer {
    return {
        entity_id: "e1",
        reference_id: 1,
        offset: 0,
        length: 0,
        field: "body",
        exact_text: "",
        prefix_text: "",
        suffix_text: "",
        ...overrides,
    };
}

const entities: ImmutableMap<string, Entity> = Map({
    e1: {
        entity_id: "e1",
        preferred_name: "Hello",
        kind: "Enzyme",
        synonyms: Set<string>(),
        confirmed: true,
    },
});

const HTML = "<p>Hello world foo bar</p>"; // plain text: "Hello world foo bar"

let elem: HTMLDivElement;

beforeEach(() => {
    mountMock.mockReset();
    unmountMock.mockReset();
    // A distinct sentinel per mount so we can assert unmount receives them.
    let n = 0;
    mountMock.mockImplementation(() => ({ instance: ++n }));
    elem = document.createElement("div");
});

describe("annotateHTMLString mount lifecycle (TICKET-23)", () => {
    test("mounts one ResourceCard per resolvable pointer and returns a cleanup", () => {
        const pointers = Map<string, Pointer>({
            p1: pointer({ offset: 0, length: 5, exact_text: "Hello" }),
            p2: pointer({ offset: 6, length: 5, exact_text: "world" }),
        });

        const cleanup = annotateHTMLString(
            elem,
            HTML,
            pointers,
            entities,
            "body",
        );

        expect(mountMock).toHaveBeenCalledTimes(2);
        expect(typeof cleanup).toBe("function");
        expect(unmountMock).not.toHaveBeenCalled();
    });

    test("cleanup unmounts exactly the cards it mounted", () => {
        const pointers = Map<string, Pointer>({
            p1: pointer({ offset: 0, length: 5, exact_text: "Hello" }),
            p2: pointer({ offset: 6, length: 5, exact_text: "world" }),
        });

        const cleanup = annotateHTMLString(
            elem,
            HTML,
            pointers,
            entities,
            "body",
        );
        const mountedInstances = mountMock.mock.results.map((r) => r.value);

        cleanup();

        expect(unmountMock).toHaveBeenCalledTimes(2);
        expect(unmountMock.mock.calls.map((c) => c[0])).toEqual(
            mountedInstances,
        );
    });

    test("re-rendering does not accumulate: each render's cleanup covers only that render", () => {
        const first = Map<string, Pointer>({
            p1: pointer({ offset: 0, length: 5, exact_text: "Hello" }),
        });
        const cleanup1 = annotateHTMLString(
            elem,
            HTML,
            first,
            entities,
            "body",
        );
        expect(mountMock).toHaveBeenCalledTimes(1);

        // Simulate the attachment tearing down before the next render.
        cleanup1();
        expect(unmountMock).toHaveBeenCalledTimes(1);

        const second = Map<string, Pointer>({
            p1: pointer({ offset: 0, length: 5, exact_text: "Hello" }),
            p2: pointer({ offset: 6, length: 5, exact_text: "world" }),
        });
        const cleanup2 = annotateHTMLString(
            elem,
            HTML,
            second,
            entities,
            "body",
        );
        expect(mountMock).toHaveBeenCalledTimes(3); // 1 + 2, not accumulating stale mounts

        unmountMock.mockClear();
        cleanup2();
        expect(unmountMock).toHaveBeenCalledTimes(2);
    });

    test("pointers that fail to resolve are neither mounted nor part of cleanup", () => {
        const pointers = Map<string, Pointer>({
            good: pointer({ offset: 0, length: 5, exact_text: "Hello" }),
            missing: pointer({ offset: 0, length: 5, exact_text: "absent" }),
        });

        const cleanup = annotateHTMLString(
            elem,
            HTML,
            pointers,
            entities,
            "body",
        );

        expect(mountMock).toHaveBeenCalledTimes(1);
        cleanup();
        expect(unmountMock).toHaveBeenCalledTimes(1);
    });
});
