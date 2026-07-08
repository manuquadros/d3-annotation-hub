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

    test("pointer edits still re-render the article", () => {
        const state = makeState();
        const { container } = renderSection(state);
        flushSync();

        const before0 = container.querySelector("#ptr_0");
        expect(before0).not.toBeNull();

        // Removing a pointer changes the pointers map → attachment re-runs.
        state.delete("ptr_1");
        flushSync();

        const after0 = container.querySelector("#ptr_0");
        expect(after0).not.toBeNull();
        expect(after0).not.toBe(before0);
        expect(container.querySelector("#ptr_1")).toBeNull();
    });
});
