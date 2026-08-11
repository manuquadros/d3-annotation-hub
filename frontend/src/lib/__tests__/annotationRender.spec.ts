import { describe, expect, test, vi, beforeEach } from "vitest";
import { Map } from "immutable";
import type { Pointer } from "$lib/types.ts";

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

import { annotateHTMLString, ArticleRenderer } from "$lib/annotation.svelte.ts";

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

        const cleanup = annotateHTMLString(elem, HTML, pointers, "body");

        expect(mountMock).toHaveBeenCalledTimes(2);
        expect(typeof cleanup).toBe("function");
        expect(unmountMock).not.toHaveBeenCalled();
    });

    test("cleanup unmounts exactly the cards it mounted", () => {
        const pointers = Map<string, Pointer>({
            p1: pointer({ offset: 0, length: 5, exact_text: "Hello" }),
            p2: pointer({ offset: 6, length: 5, exact_text: "world" }),
        });

        const cleanup = annotateHTMLString(elem, HTML, pointers, "body");
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
        const cleanup1 = annotateHTMLString(elem, HTML, first, "body");
        expect(mountMock).toHaveBeenCalledTimes(1);

        // Simulate the attachment tearing down before the next render.
        cleanup1();
        expect(unmountMock).toHaveBeenCalledTimes(1);

        const second = Map<string, Pointer>({
            p1: pointer({ offset: 0, length: 5, exact_text: "Hello" }),
            p2: pointer({ offset: 6, length: 5, exact_text: "world" }),
        });
        const cleanup2 = annotateHTMLString(elem, HTML, second, "body");
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

        const cleanup = annotateHTMLString(elem, HTML, pointers, "body");

        expect(mountMock).toHaveBeenCalledTimes(1);
        cleanup();
        expect(unmountMock).toHaveBeenCalledTimes(1);
    });
});

describe("ArticleRenderer incremental updates (TICKET-23)", () => {
    // A faithful stand-in for ResourceCard: it adopts the extracted fragment
    // into a root of its own, so the container keeps its text between updates
    // exactly as the real card does.
    beforeEach(() => {
        let n = 0;
        mountMock.mockImplementation(
            (
                _component: unknown,
                options: {
                    target: HTMLElement;
                    props: { fragment: DocumentFragment };
                },
            ) => {
                const root = document.createElement("span");
                root.className = "annotation-highlight";
                root.append(options.props.fragment);
                options.target.append(root);
                return { id: ++n, root };
            },
        );
        unmountMock.mockImplementation((instance: { root: HTMLElement }) => {
            instance.root.remove();
        });
    });

    const hello = pointer({ offset: 0, length: 5, exact_text: "Hello" });
    const world = pointer({ offset: 6, length: 5, exact_text: "world" });
    const foo = pointer({ offset: 12, length: 3, exact_text: "foo" });

    test("re-updating with the same pointers touches no cards", () => {
        const pointers = Map<string, Pointer>({ p1: hello, p2: world });
        const renderer = new ArticleRenderer(elem, HTML, "body");
        renderer.update(pointers);
        expect(mountMock).toHaveBeenCalledTimes(2);

        renderer.update(pointers);

        expect(mountMock).toHaveBeenCalledTimes(2);
        expect(unmountMock).not.toHaveBeenCalled();
    });

    test("deleting a pointer unmounts only that pointer's card", () => {
        const renderer = new ArticleRenderer(elem, HTML, "body");
        renderer.update(Map<string, Pointer>({ p1: hello, p2: world }));
        const [firstCard, secondCard] = mountMock.mock.results.map(
            (r) => r.value,
        );

        renderer.update(Map<string, Pointer>({ p1: hello }));

        expect(unmountMock.mock.calls.map((c) => c[0])).toEqual([secondCard]);
        expect(mountMock).toHaveBeenCalledTimes(2);
        expect(elem.contains(firstCard.root)).toBe(true);
        expect(elem.textContent).toBe("Hello world foo bar");
        expect(elem.querySelector("#p2")).toBeNull();
    });

    test("adding a pointer mounts only the new card", () => {
        const renderer = new ArticleRenderer(elem, HTML, "body");
        renderer.update(Map<string, Pointer>({ p1: hello, p2: world }));
        const before = mountMock.mock.results.map((r) => r.value);

        renderer.update(
            Map<string, Pointer>({ p1: hello, p2: world, p3: foo }),
        );

        expect(mountMock).toHaveBeenCalledTimes(3);
        expect(unmountMock).not.toHaveBeenCalled();
        for (const card of before) expect(elem.contains(card.root)).toBe(true);
        expect(elem.querySelector("#p3")?.textContent).toBe("foo");
        expect(elem.textContent).toBe("Hello world foo bar");
    });

    test("destroy unmounts the cards still live after incremental updates", () => {
        const renderer = new ArticleRenderer(elem, HTML, "body");
        renderer.update(Map<string, Pointer>({ p1: hello, p2: world }));
        renderer.update(Map<string, Pointer>({ p1: hello, p3: foo }));
        unmountMock.mockClear();

        renderer.destroy();

        expect(unmountMock).toHaveBeenCalledTimes(2);
    });

    test("overlapping spans fall back to a full rebuild", () => {
        const renderer = new ArticleRenderer(elem, HTML, "body");
        renderer.update(Map<string, Pointer>({ p1: hello, p2: world }));
        mountMock.mockClear();
        unmountMock.mockClear();

        renderer.update(
            Map<string, Pointer>({
                p1: hello,
                p2: world,
                p3: pointer({ offset: 3, length: 5, exact_text: "lo wo" }),
            }),
        );

        expect(unmountMock).toHaveBeenCalledTimes(2);
        expect(mountMock).toHaveBeenCalledTimes(3);
    });

    // plain text: "Alpha beta gamma delta"
    const RICH = "<p>Alpha <b>beta</b> gamma delta</p>";
    const alpha = pointer({ offset: 0, length: 5, exact_text: "Alpha" });
    const beta = pointer({ offset: 6, length: 4, exact_text: "beta" });
    const delta = pointer({ offset: 17, length: 5, exact_text: "delta" });
    // Starts inside <b> and ends outside it.
    const betaGamma = pointer({
        offset: 6,
        length: 10,
        exact_text: "beta gamma",
    });

    function rebuild(pointers: Map<string, Pointer>): string {
        const fresh = document.createElement("div");
        new ArticleRenderer(fresh, RICH, "body").update(pointers);
        return fresh.innerHTML;
    }

    test("patching to a pointer set yields the DOM a rebuild would", () => {
        const target = Map<string, Pointer>({ p1: alpha, p3: delta });
        const renderer = new ArticleRenderer(elem, RICH, "body");
        renderer.update(target.set("p2", beta));
        renderer.update(target);

        expect(elem.innerHTML).toBe(rebuild(target));
    });

    test("removing a mark that crossed an element boundary rebuilds", () => {
        const target = Map<string, Pointer>({ p1: alpha });
        const renderer = new ArticleRenderer(elem, RICH, "body");
        renderer.update(target.set("p2", betaGamma));
        mountMock.mockClear();
        unmountMock.mockClear();

        renderer.update(target);

        // Putting the extracted content back cannot undo the <b> split, so the
        // whole article is re-rendered instead.
        expect(unmountMock).toHaveBeenCalledTimes(2);
        expect(mountMock).toHaveBeenCalledTimes(1);
        expect(elem.innerHTML).toBe(rebuild(target));
    });
});
