import { describe, test, expect } from "vitest";
import { render } from "@testing-library/svelte";
import { flushSync } from "svelte";
import ArticleSection from "$lib/components/ArticleSection.svelte";
import { AnnotationState } from "$lib/annotation.svelte.ts";
import type { EditorState } from "$lib/types.ts";

const BODY = "Bacteria were found and bacteria appeared again.";

function makeState(): AnnotationState {
    return new AnnotationState({
        user: {
            user_id: "550e8400-e29b-41d4-a716-446655440000",
            email: "test@example.com",
        },
        project_id: 1,
        reference: {
            reference_id: 1,
            pubmed_id: 12345678,
            pmc_id: 1234567,
            pmc_open: true,
            doi: "10.0000/test",
            authors: "Author A",
            title: "Test Article",
            journal: "Journal",
            volume: "1",
            number: null,
            pages: "1-10",
            year: 2020,
            abstract: null,
            body: BODY,
        },
        entities: [
            {
                entity_id: "entity-1",
                preferred_name: "Bacteria",
                kind: "Bacteria",
                synonyms: [],
                confirmed: true,
                uri: null,
            },
        ],
        // Two mentions of the entity → pointers keyed ptr_0, ptr_1.
        pointers: [
            { entity_id: "entity-1", reference_id: 1, offset: 0, length: 8 },
            { entity_id: "entity-1", reference_id: 1, offset: 24, length: 8 },
        ],
        relations: [],
        completed: false,
    });
}

function renderSection(state: AnnotationState) {
    return render(ArticleSection, {
        props: { html: BODY, field: "body" as const },
        context: new Map<string, unknown>([
            ["annotationState", state],
            ["editorState", { value: null as unknown as EditorState }],
        ]),
    });
}

describe("ArticleSection render reactivity", () => {
    test("marks each resolvable pointer with a span carrying its pointer id", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();

        expect(container.querySelector("#ptr_0")).not.toBeNull();
        expect(container.querySelector("#ptr_1")).not.toBeNull();
    });

    test("entity-metadata edits do not re-render the article", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();

        // Capture the actual DOM nodes; a re-render replaces innerHTML, so the
        // nodes would change identity if the attachment re-ran.
        const before0 = container.querySelector("#ptr_0");
        const before1 = container.querySelector("#ptr_1");
        expect(before0).not.toBeNull();

        state.updateEntityPreferredName("entity-1", "Renamed");
        state.updateEntityKind("entity-1", "Enzyme");
        state.addSynonym("entity-1", "bug");
        flushSync();

        expect(container.querySelector("#ptr_0")).toBe(before0);
        expect(container.querySelector("#ptr_1")).toBe(before1);
    });

    test("deleting a pointer unmarks only that span", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();

        const before0 = container.querySelector("#ptr_0");
        expect(before0).not.toBeNull();

        state.delete("ptr_1");
        flushSync();

        // The surviving mark and the ResourceCard mounted inside it are the
        // same nodes: a rebuild would have replaced both.
        expect(container.querySelector("#ptr_0")).toBe(before0);
        expect(container.querySelector("#ptr_1")).toBeNull();
        expect(container.querySelector("#article-body")?.textContent).toBe(
            BODY,
        );
    });

    test("deleting a pointer keeps the surviving cards mounted", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();

        const card0 = container.querySelector("#ptr_0 .annotation-highlight");
        expect(card0).not.toBeNull();

        state.delete("ptr_1");
        flushSync();

        // ResourceCard renders this span itself, so an unmount+remount would
        // yield a different node even though the id and text match.
        expect(container.querySelector("#ptr_0 .annotation-highlight")).toBe(
            card0,
        );
    });

    test("adding a pointer marks only the new span", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();

        const before0 = container.querySelector("#ptr_0");
        const before1 = container.querySelector("#ptr_1");
        const card0 = container.querySelector("#ptr_0 .annotation-highlight");

        // "found" occupies offsets 14-19 of BODY and overlaps neither pointer.
        state.add("Enzyme", "found", [{ offset: 14, length: 5 }], "body");
        flushSync();

        expect(container.querySelector("#ptr_0")).toBe(before0);
        expect(container.querySelector("#ptr_1")).toBe(before1);
        expect(container.querySelector("#ptr_0 .annotation-highlight")).toBe(
            card0,
        );
        expect(container.querySelector("#ptr_2")?.textContent).toBe("found");
        expect(container.querySelector("#article-body")?.textContent).toBe(
            BODY,
        );
    });

    test("moving a pointer re-marks it without disturbing the others", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();

        const before0 = container.querySelector("#ptr_0");
        const before1 = container.querySelector("#ptr_1");

        // "appeared" occupies offsets 33-41.
        state.updatePointerOffsets("ptr_1", 33, 8);
        flushSync();

        expect(container.querySelector("#ptr_0")).toBe(before0);
        expect(container.querySelector("#ptr_1")).not.toBe(before1);
        expect(container.querySelector("#ptr_1")?.textContent).toBe("appeared");
        expect(container.querySelector("#article-body")?.textContent).toBe(
            BODY,
        );
    });

    test("undoing back to the original pointer set restores the same DOM", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();
        const body = container.querySelector("#article-body")!;
        const rebuilt = body.innerHTML;

        state.add("Enzyme", "found", [{ offset: 14, length: 5 }], "body");
        flushSync();
        state.undo();
        flushSync();

        expect(body.innerHTML).toBe(rebuilt);
        expect(body.textContent).toBe(BODY);
    });
});
