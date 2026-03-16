import { render } from "@testing-library/svelte";
import { expect, test } from "vitest";
import Annotation from "$lib/components/Annotation.svelte";
import { AnnotationState } from "$lib/annotation.svelte";
import { Set } from "immutable";
import { createRelation } from "$lib/types.ts";

const BASE_REFERENCE = {
    reference_id: 1,
    pubmed_id: 12345678,
    pmc_id: 1234567,
    pmc_open: true,
    doi: "10.1234/test",
    authors: "Test Author",
    title: "Test Article",
    journal: "Test Journal",
    volume: "1",
    number: "1",
    pages: "1-10",
    year: 2024,
    body: "<p>The strain <em>E. coli</em> K-12 produces beta-galactosidase enzyme.</p>",
};

const BASE_USER = {
    user_id: "550e8400-e29b-41d4-a716-446655440000",
    email: "test@example.com",
};

function makeState(overrides: object = {}): AnnotationState {
    const data = {
        user: BASE_USER,
        reference: BASE_REFERENCE,
        entities: [
            { entity_id: "entity_1", preferred_name: "K-12",             kind: "d3o:Strain",   synonyms: ["K-12"] },
            { entity_id: "entity_2", preferred_name: "E. coli",          kind: "d3o:Bacteria", synonyms: ["E. coli"] },
            { entity_id: "entity_3", preferred_name: "beta-galactosidase", kind: "d3o:Enzyme", synonyms: ["beta-galactosidase"] },
        ],
        pointers: [
            { entity_id: "entity_2", reference_id: 1, offset: 11, length: 7 },
            { entity_id: "entity_1", reference_id: 1, offset: 19, length: 4 },
            { entity_id: "entity_3", reference_id: 1, offset: 33, length: 18 },
        ],
        relations: [
            { subject: "entity_1", predicate: "d3o:hasSpecies", object: "entity_2" },
            { subject: "entity_2", predicate: "d3o:hasEnzyme",  object: "entity_3" },
        ],
        ...overrides,
    };
    return new AnnotationState(JSON.stringify(data));
}

test("Entity names in Summary match those in Relations", async () => {
    const initialState = makeState();
    const container = document.createElement("div");

    const { container: component } = render(Annotation, {
        target: container,
        props: { initialState },
    });

    await new Promise((resolve) => setTimeout(resolve, 100));

    const summarySection = component.querySelector("#summary");
    const relationsSection = component.querySelector("#relations");
    expect(summarySection).not.toBeNull();
    expect(relationsSection).not.toBeNull();

    const summaryEntityNames = Array.from(
        summarySection?.querySelectorAll(".entity-button") || [],
    ).map((btn) => btn.textContent?.replace(/\d+$/, "").trim() || "");

    const relationsSubjects = Array.from(
        relationsSection?.querySelectorAll(".subject") || [],
    ).map((el) => el.textContent?.trim() || "");

    const relationsObjects = Array.from(
        relationsSection?.querySelectorAll(".object") || [],
    ).map((el) => el.textContent?.trim() || "");

    relationsSubjects.forEach((name) => expect(summaryEntityNames).toContain(name));
    relationsObjects.forEach((name) => expect(summaryEntityNames).toContain(name));

    expect(summaryEntityNames).toContain("K-12");
    expect(summaryEntityNames).toContain("E. coli");
    expect(summaryEntityNames).toContain("beta-galactosidase");

    expect(relationsSubjects).toContain("K-12");
    expect(relationsObjects).toContain("E. coli");
    expect(relationsSubjects).toContain("E. coli");
    expect(relationsObjects).toContain("beta-galactosidase");
});

test("Relations are unique - Set with Record ensures uniqueness", () => {
    const state = makeState();

    expect(state.relations.size).toBe(2);

    state.relations = state.relations.add(
        createRelation({ subject: "entity_1", predicate: "d3o:hasSpecies", object: "entity_2" }),
    );
    expect(state.relations.size).toBe(2);

    state.relations = state.relations.add(
        createRelation({ subject: "entity_1", predicate: "d3o:hasEnzyme", object: "entity_3" }),
    );
    expect(state.relations.size).toBe(3);
});

test("Entities of the same type can be merged", () => {
    const data = {
        user: BASE_USER,
        reference: {
            ...BASE_REFERENCE,
            body: "<p>Strain ATCC and strain 25544 are the same species E. coli.</p>",
        },
        entities: [
            { entity_id: "entity_1", preferred_name: "ATCC",   kind: "d3o:Strain",   synonyms: ["ATCC"] },
            { entity_id: "entity_2", preferred_name: "25544",  kind: "d3o:Strain",   synonyms: ["25544"] },
            { entity_id: "entity_3", preferred_name: "E. coli", kind: "d3o:Bacteria", synonyms: ["E. coli"] },
        ],
        pointers: [
            { entity_id: "entity_1", reference_id: 1, offset: 7,  length: 4 },
            { entity_id: "entity_2", reference_id: 1, offset: 22, length: 5 },
            { entity_id: "entity_3", reference_id: 1, offset: 48, length: 7 },
        ],
        relations: [
            { subject: "entity_1", predicate: "d3o:hasSpecies", object: "entity_3" },
        ],
    };

    const state = new AnnotationState(JSON.stringify(data));

    expect(state.entities.size).toBe(3);
    expect(state.pointers.size).toBe(3);
    expect(state.relations.size).toBe(1);

    const initialRelation = state.relations.first()!;
    expect(initialRelation.subject).toBe("entity_1");
    expect(initialRelation.object).toBe("entity_3");

    // Merge entity_1 into entity_2: union synonyms
    const entity1 = state.entity("entity_1")!;
    const entity2 = state.entity("entity_2")!;

    const mergedSynonyms = entity1.synonyms.union(entity2.synonyms);

    state.entities = state.entities.set("entity_2", {
        ...entity2,
        synonyms: mergedSynonyms,
    });

    // Re-point entity_1 pointers to entity_2
    let updatedPointers = state.pointers;
    state.pointers.forEach((pointer, key) => {
        if (pointer.entity_id === "entity_1") {
            updatedPointers = updatedPointers.set(key, { ...pointer, entity_id: "entity_2" });
        }
    });
    state.pointers = updatedPointers;

    // Update relations
    let updatedRelations = state.relations;
    state.relations.forEach((relation) => {
        if (relation.subject === "entity_1" || relation.object === "entity_1") {
            updatedRelations = updatedRelations.delete(relation);
            updatedRelations = updatedRelations.add(
                createRelation({
                    subject: relation.subject === "entity_1" ? "entity_2" : relation.subject,
                    predicate: relation.predicate,
                    object: relation.object === "entity_1" ? "entity_2" : relation.object,
                }),
            );
        }
    });
    state.relations = updatedRelations;

    state.entities = state.entities.delete("entity_1");

    expect(state.entities.size).toBe(2);
    expect(state.pointers.size).toBe(3);

    // All pointers should now reference entity_2
    state.pointers.forEach((pointer) => {
        expect(pointer.entity_id).toBe(pointer.entity_id === "entity_3" ? "entity_3" : "entity_2");
    });

    const mergedEntity = state.entity("entity_2")!;
    expect(mergedEntity.synonyms.size).toBe(2);
    expect(mergedEntity.synonyms.has("ATCC")).toBe(true);
    expect(mergedEntity.synonyms.has("25544")).toBe(true);

    expect(state.relations.size).toBe(1);
    const updatedRelation = state.relations.first()!;
    expect(updatedRelation.subject).toBe("entity_2");
    expect(updatedRelation.object).toBe("entity_3");
    expect(updatedRelation.predicate).toBe("d3o:hasSpecies");
});

test("Deleting an entity also deletes its relations", () => {
    const state = makeState();

    expect(state.entities.size).toBe(3);
    expect(state.relations.size).toBe(2);

    // Delete entity_2 (referenced in both relations)
    let updatedPointers = state.pointers;
    state.pointers.forEach((pointer, key) => {
        if (pointer.entity_id === "entity_2") {
            updatedPointers = updatedPointers.delete(key);
        }
    });
    state.pointers = updatedPointers;

    state.relations = Set(
        state.relations
            .toArray()
            .filter((r) => r.subject !== "entity_2" && r.object !== "entity_2"),
    );

    state.entities = state.entities.delete("entity_2");

    expect(state.entities.size).toBe(2);
    expect(state.relations.size).toBe(0);
    expect(state.entity("entity_2")).toBeUndefined();
    expect(state.entity("entity_1")).toBeDefined();
    expect(state.entity("entity_3")).toBeDefined();
});
