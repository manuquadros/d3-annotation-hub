import { describe, it, expect } from "vitest";
import {
    computeReviewModel,
    pointerKey,
    type ReviewInput,
    type ReviewPointer,
    type ReviewRelation,
} from "$lib/utils/curationReview";

function ptr(
    entity_id: string,
    over: Partial<ReviewPointer> = {},
): ReviewPointer {
    return {
        reference_id: 1,
        entity_id,
        offset: 5,
        length: 4,
        field: "abstract",
        exact_text: "",
        prefix_text: "",
        suffix_text: "",
        ...over,
    };
}

function rel(subject: string, object: string): ReviewRelation {
    return { relation_id: null, predicate: "produces", subject, object };
}

function input(entityId: string, over: Partial<ReviewInput> = {}): ReviewInput {
    return {
        entities: {
            [entityId]: {
                entity_id: entityId,
                preferred_name: "E. coli",
                kind: "Bacterium",
                confirmed: false,
            },
        },
        snapshots: [
            {
                user_id: "u1",
                email: "a@x.example",
                reference_id: 1,
                pointers: [ptr(entityId)],
                relations: [],
                created_at: "2026-01-01",
            },
        ],
        curated_pointers: [],
        curated_relations: [],
        ...over,
    };
}

describe("computeReviewModel", () => {
    it("keys pointers and entities by the snapshot's CURIE", () => {
        const model = computeReviewModel(input("PROP:1"));
        expect([...model.pointerData.keys()]).toContain(
            pointerKey(ptr("PROP:1")),
        );
        expect(
            model.pointerData.get(pointerKey(ptr("PROP:1")))!.entity_id,
        ).toBe("PROP:1");
        expect(model.sortedEntityIds).toEqual(["PROP:1"]);
        expect([...model.entityAnnotators.keys()]).toEqual(["PROP:1"]);
    });

    it("reflects a renamed CURIE when the re-fetched data changes", () => {
        // Simulates the post-rename reload: the snapshot pointer and the
        // entities map now carry NEW:2 instead of PROP:1. The model — and thus
        // the save payload built from model.pointerData — must follow.
        const renamed = computeReviewModel(input("NEW:2"));
        expect(renamed.sortedEntityIds).toEqual(["NEW:2"]);
        const key = pointerKey(ptr("NEW:2"));
        expect(renamed.pointerData.get(key)!.entity_id).toBe("NEW:2");
        // The stale key is gone — a save keyed off the old CURIE can't happen.
        expect(renamed.pointerData.has(pointerKey(ptr("PROP:1")))).toBe(false);
    });

    it("marks previously-curated pointers as accepted", () => {
        const model = computeReviewModel(
            input("PROP:1", { curated_pointers: [ptr("PROP:1")] }),
        );
        expect(model.hasSavedCuration).toBe(true);
        expect(model.acceptedPointerKeys.has(pointerKey(ptr("PROP:1")))).toBe(
            true,
        );
        expect(model.acceptedEntityIds.has("PROP:1")).toBe(true);
    });

    it("aggregates annotator agreement per pointer", () => {
        const base = input("PROP:1");
        base.snapshots.push({
            user_id: "u2",
            email: "b@x.example",
            reference_id: 1,
            pointers: [ptr("PROP:1")],
            relations: [rel("PROP:1", "OBJ:1")],
            created_at: "2026-01-02",
        });
        const model = computeReviewModel(base);
        expect(
            model.pointerAnnotators.get(pointerKey(ptr("PROP:1")))!.size,
        ).toBe(2);
        expect(model.relationData.size).toBe(1);
    });
});
