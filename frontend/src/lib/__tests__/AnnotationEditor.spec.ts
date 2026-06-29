import { describe, test, expect, vi, beforeEach } from "vitest";
import { render } from "@testing-library/svelte";
import AnnotationEditor from "$lib/components/AnnotationEditor.svelte";
import { AnnotationState } from "$lib/annotation.svelte.ts";

vi.mock("$lib/api.ts", () => ({
    fetchEntityTypes: vi.fn().mockResolvedValue([]),
    searchEntities: vi.fn().mockResolvedValue([]),
}));

beforeEach(() => {
    HTMLDialogElement.prototype.showModal = vi.fn();
    HTMLDialogElement.prototype.close = vi.fn();
});

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
            body: "Bacteria were found and bacteria appeared again.",
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
        pointers: [
            { entity_id: "entity-1", reference_id: 1, offset: 0, length: 8 },
            { entity_id: "entity-1", reference_id: 1, offset: 24, length: 8 },
        ],
        relations: [],
        completed: false,
    });
}

describe("AnnotationEditor — edit-entity mode", () => {
    test("renders one mention button per pointer when multiple pointers share an entity", () => {
        const annotationState = makeState();

        const { container } = render(AnnotationEditor, {
            props: {
                editorState: { mode: "edit-entity", entityId: "entity-1" },
            },
            context: new Map([["annotationState", annotationState]]),
        });

        // Two pointers reference entity-1, so two .mention divs must appear.
        // Before the fix, Svelte threw each_key_duplicate here because p.entity_id
        // was used as the each key and all pointers share the same entity_id.
        expect(container.querySelectorAll(".mention")).toHaveLength(2);
    });
});
