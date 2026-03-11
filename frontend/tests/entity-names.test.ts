import { render } from "@testing-library/svelte";
import { expect, test } from "vitest";
import Annotation from "$lib/components/Annotation.svelte";
import { AnnotationState } from "$lib/annotation.svelte";
import { Map, Set } from "immutable";
import { createRelation } from "$lib/types.ts";

/**
 * Creates test annotation state with entities, pointers, and relations.
 */
/**
 * Creates test annotation state WITHOUT designations in JSON.
 * This simulates real conditions where entity names must be extracted from pointer text.
 */
function createTestAnnotationStateWithoutDesignations(): AnnotationState {
    const testUserId = "550e8400-e29b-41d4-a716-446655440000";

    const annotationData = {
        user: {
            user_id: testUserId,
            email: "test@example.com",
        },
        reference: {
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
        },
        entities: {
            "entity_1": {
                entity_id: "entity_1",
                kind: "d3o:Strain",
            },
            "entity_2": {
                entity_id: "entity_2",
                kind: "d3o:Bacteria",
            },
            "entity_3": {
                entity_id: "entity_3",
                kind: "d3o:Enzyme",
            },
        },
        pointers: {
            1: {
                pointer_id: 1,
                user_id: testUserId,
                entity_id: "entity_2",
                reference_id: 1,
                offset: 11,
                length: 7,
            },
            2: {
                pointer_id: 2,
                user_id: testUserId,
                entity_id: "entity_1",
                reference_id: 1,
                offset: 19,
                length: 4,
            },
            3: {
                pointer_id: 3,
                user_id: testUserId,
                entity_id: "entity_3",
                reference_id: 1,
                offset: 33,
                length: 18,
            },
        },
        relations: [
            {
                subject: "entity_1",
                predicate: "d3o:hasSpecies",
                object: "entity_2",
            },
            {
                subject: "entity_2",
                predicate: "d3o:hasEnzyme",
                object: "entity_3",
            },
        ],
    };

    return new AnnotationState(JSON.stringify(annotationData));
}

/**
 * Creates test annotation state WITH designations in JSON.
 * This simulates data loaded from the backend that already has designations.
 */
function createTestAnnotationStateWithDesignations(): AnnotationState {
    const testUserId = "550e8400-e29b-41d4-a716-446655440000";

    const annotationData = {
        user: {
            user_id: testUserId,
            email: "test@example.com",
        },
        reference: {
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
        },
        entities: {
            "entity_1": {
                entity_id: "entity_1",
                kind: "d3o:Strain",
                designations: ["K-12"],
            },
            "entity_2": {
                entity_id: "entity_2",
                kind: "d3o:Bacteria",
                designations: ["E. coli"],
            },
            "entity_3": {
                entity_id: "entity_3",
                kind: "d3o:Enzyme",
                designations: ["beta-galactosidase"],
            },
        },
        pointers: {
            1: {
                pointer_id: 1,
                user_id: testUserId,
                entity_id: "entity_2",
                reference_id: 1,
                offset: 11,
                length: 7,
            },
            2: {
                pointer_id: 2,
                user_id: testUserId,
                entity_id: "entity_1",
                reference_id: 1,
                offset: 19,
                length: 4,
            },
            3: {
                pointer_id: 3,
                user_id: testUserId,
                entity_id: "entity_3",
                reference_id: 1,
                offset: 33,
                length: 18,
            },
        },
        relations: [
            {
                subject: "entity_1",
                predicate: "d3o:hasSpecies",
                object: "entity_2",
            },
            {
                subject: "entity_2",
                predicate: "d3o:hasEnzyme",
                object: "entity_3",
            },
        ],
    };

    return new AnnotationState(JSON.stringify(annotationData));
}

test("Entity names in Summary match those in Relations (with designations in JSON)", async () => {
    const initialState = createTestAnnotationStateWithDesignations();
    const container = document.createElement("div");

    const { container: component } = render(Annotation, {
        target: container,
        props: {
            initialState,
        },
    });

    // Wait for component to render
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Get the summary section
    const summarySection = component.querySelector("#summary");
    expect(summarySection).not.toBeNull();

    // Get the relations section
    const relationsSection = component.querySelector("#relations");
    expect(relationsSection).not.toBeNull();

    // Extract entity names from summary buttons
    const summaryButtons = Array.from(
        summarySection?.querySelectorAll(".entity-button") || [],
    );
    const summaryEntityNames = summaryButtons.map((btn) => {
        // Extract the text content, excluding the count badge
        const fullText = btn.textContent || "";
        // Remove the count (last number in the button)
        return fullText.replace(/\d+$/, "").trim();
    });

    console.log("Summary entity names (with designations):", summaryEntityNames);

    // Extract entity names from relations
    const relationsSubjects = Array.from(
        relationsSection?.querySelectorAll(".subject") || [],
    ).map((el) => el.textContent?.trim() || "");

    const relationsObjects = Array.from(
        relationsSection?.querySelectorAll(".object") || [],
    ).map((el) => el.textContent?.trim() || "");

    console.log("Relations subjects (with designations):", relationsSubjects);
    console.log("Relations objects (with designations):", relationsObjects);

    // Check that all relation subjects are in the summary
    relationsSubjects.forEach((subjectName) => {
        expect(summaryEntityNames).toContain(subjectName);
    });

    // Check that all relation objects are in the summary
    relationsObjects.forEach((objectName) => {
        expect(summaryEntityNames).toContain(objectName);
    });

    // Specific checks for our test data
    expect(summaryEntityNames).toContain("K-12");
    expect(summaryEntityNames).toContain("E. coli");
    expect(summaryEntityNames).toContain("beta-galactosidase");

    // Check that relations display the same names
    expect(relationsSubjects).toContain("K-12");
    expect(relationsObjects).toContain("E. coli");

    expect(relationsSubjects).toContain("E. coli");
    expect(relationsObjects).toContain("beta-galactosidase");
});

test("Entity names in Summary match those in Relations (WITHOUT designations - extracted from pointers)", async () => {
    const initialState = createTestAnnotationStateWithoutDesignations();
    const container = document.createElement("div");

    const { container: component } = render(Annotation, {
        target: container,
        props: {
            initialState,
        },
    });

    // Wait for component to render
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Get the summary section
    const summarySection = component.querySelector("#summary");
    expect(summarySection).not.toBeNull();

    // Get the relations section
    const relationsSection = component.querySelector("#relations");
    expect(relationsSection).not.toBeNull();

    // Extract entity names from summary buttons
    const summaryButtons = Array.from(
        summarySection?.querySelectorAll(".entity-button") || [],
    );
    const summaryEntityNames = summaryButtons.map((btn) => {
        const fullText = btn.textContent || "";
        return fullText.replace(/\d+$/, "").trim();
    });

    console.log("Summary entity names (without designations):", summaryEntityNames);

    // Extract entity names from relations
    const relationsSubjects = Array.from(
        relationsSection?.querySelectorAll(".subject") || [],
    ).map((el) => el.textContent?.trim() || "");

    const relationsObjects = Array.from(
        relationsSection?.querySelectorAll(".object") || [],
    ).map((el) => el.textContent?.trim() || "");

    console.log("Relations subjects (without designations):", relationsSubjects);
    console.log("Relations objects (without designations):", relationsObjects);

    // Check that all relation subjects are in the summary
    relationsSubjects.forEach((subjectName) => {
        expect(summaryEntityNames).toContain(subjectName);
    });

    // Check that all relation objects are in the summary
    relationsObjects.forEach((objectName) => {
        expect(summaryEntityNames).toContain(objectName);
    });

    // Specific checks - names should be extracted from pointer text
    expect(summaryEntityNames).toContain("K-12");
    expect(summaryEntityNames).toContain("E. coli");
    expect(summaryEntityNames).toContain("beta-galactosidase");

    // Check that relations display the same names extracted from pointers
    expect(relationsSubjects).toContain("K-12");
    expect(relationsObjects).toContain("E. coli");

    expect(relationsSubjects).toContain("E. coli");
    expect(relationsObjects).toContain("beta-galactosidase");
});

test("Relations are unique - Set with Record ensures uniqueness", () => {
    const initialState = createTestAnnotationStateWithDesignations();

    // Initial state has 2 relations
    expect(initialState.relations.size).toBe(2);

    // Try to add the same relation again using createRelation
    const duplicateRelation = createRelation({
        subject: "entity_1",
        predicate: "d3o:hasSpecies",
        object: "entity_2",
    });

    // Add the duplicate relation
    initialState.relations = initialState.relations.add(duplicateRelation);

    // Should still be size 2 because Set with Record prevents duplicates automatically
    expect(initialState.relations.size).toBe(2);

    // Add a different relation
    const newRelation = createRelation({
        subject: "entity_1",
        predicate: "d3o:hasEnzyme",
        object: "entity_3",
    });

    initialState.relations = initialState.relations.add(newRelation);

    // Should now be size 3
    expect(initialState.relations.size).toBe(3);
});

test("Entities of the same type can be merged", () => {
    const testUserId = "550e8400-e29b-41d4-a716-446655440000";

    // Create state with two strain entities with different designations
    // and a bacteria entity to test relation updates
    const annotationData = {
        user: {
            user_id: testUserId,
            email: "test@example.com",
        },
        reference: {
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
            body: "<p>Strain ATCC and strain 25544 are the same species E. coli.</p>",
        },
        entities: {
            "entity_1": {
                entity_id: "entity_1",
                kind: "d3o:Strain",
                designations: ["ATCC"],
            },
            "entity_2": {
                entity_id: "entity_2",
                kind: "d3o:Strain",
                designations: ["25544"],
            },
            "entity_3": {
                entity_id: "entity_3",
                kind: "d3o:Bacteria",
                designations: ["E. coli"],
            },
        },
        pointers: {
            1: {
                pointer_id: 1,
                user_id: testUserId,
                entity_id: "entity_1",
                reference_id: 1,
                offset: 7,
                length: 4,
            },
            2: {
                pointer_id: 2,
                user_id: testUserId,
                entity_id: "entity_2",
                reference_id: 1,
                offset: 22,
                length: 5,
            },
            3: {
                pointer_id: 3,
                user_id: testUserId,
                entity_id: "entity_3",
                reference_id: 1,
                offset: 48,
                length: 7,
            },
        },
        relations: [
            {
                subject: "entity_1",
                predicate: "d3o:hasSpecies",
                object: "entity_3",
            },
        ],
    };

    const state = new AnnotationState(JSON.stringify(annotationData));

    // Initial state: 3 entities, 1 relation
    expect(state.entities.size).toBe(3);
    expect(state.pointers.size).toBe(3);
    expect(state.relations.size).toBe(1);

    // Verify initial relation references entity_1
    const initialRelation = state.relations.first()!;
    expect(initialRelation.subject).toBe("entity_1");
    expect(initialRelation.object).toBe("entity_3");

    // Simulate merge: entity_1 merged into entity_2
    const entity1 = state.entity("entity_1")!;
    const entity2 = state.entity("entity_2")!;

    // Union designations
    const mergedDesignations = (entity1.designations || Set<string>()).union(
        entity2.designations || Set<string>(),
    );

    // Update entity_2 with merged designations
    state.entities = state.entities.set("entity_2", {
        ...entity2,
        designations: mergedDesignations,
    });

    // Update all pointers from entity_1 to entity_2
    let updatedPointers = state.pointers;
    state.pointers.forEach((pointer) => {
        if (pointer.entity_id === "entity_1") {
            updatedPointers = updatedPointers.set(pointer.pointer_id, {
                ...pointer,
                entity_id: "entity_2",
            });
        }
    });
    state.pointers = updatedPointers;

    // Update all relations that reference entity_1
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

    // Remove entity_1
    state.entities = state.entities.delete("entity_1");

    // After merge: 2 entities (entity_2 and entity_3)
    expect(state.entities.size).toBe(2);
    expect(state.pointers.size).toBe(3);

    // All pointers for entity_1 should now point to entity_2
    state.pointers.forEach((pointer) => {
        if (pointer.pointer_id === 1 || pointer.pointer_id === 2) {
            expect(pointer.entity_id).toBe("entity_2");
        }
    });

    // Entity_2 should have both designations
    const mergedEntity = state.entity("entity_2")!;
    expect(mergedEntity.designations?.size).toBe(2);
    expect(mergedEntity.designations?.has("ATCC")).toBe(true);
    expect(mergedEntity.designations?.has("25544")).toBe(true);

    // Relation should now reference entity_2 instead of entity_1
    expect(state.relations.size).toBe(1);
    const updatedRelation = state.relations.first()!;
    expect(updatedRelation.subject).toBe("entity_2");
    expect(updatedRelation.object).toBe("entity_3");
    expect(updatedRelation.predicate).toBe("d3o:hasSpecies");
});

test("Deleting an entity also deletes its relations", () => {
    const testUserId = "550e8400-e29b-41d4-a716-446655440000";

    const annotationData = {
        user: {
            user_id: testUserId,
            email: "test@example.com",
        },
        reference: {
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
        },
        entities: {
            "entity_1": {
                entity_id: "entity_1",
                kind: "d3o:Strain",
                designations: ["K-12"],
            },
            "entity_2": {
                entity_id: "entity_2",
                kind: "d3o:Bacteria",
                designations: ["E. coli"],
            },
            "entity_3": {
                entity_id: "entity_3",
                kind: "d3o:Enzyme",
                designations: ["beta-galactosidase"],
            },
        },
        pointers: {
            1: {
                pointer_id: 1,
                user_id: testUserId,
                entity_id: "entity_2",
                reference_id: 1,
                offset: 11,
                length: 7,
            },
            2: {
                pointer_id: 2,
                user_id: testUserId,
                entity_id: "entity_1",
                reference_id: 1,
                offset: 19,
                length: 4,
            },
            3: {
                pointer_id: 3,
                user_id: testUserId,
                entity_id: "entity_3",
                reference_id: 1,
                offset: 33,
                length: 18,
            },
        },
        relations: [
            {
                subject: "entity_1",
                predicate: "d3o:hasSpecies",
                object: "entity_2",
            },
            {
                subject: "entity_2",
                predicate: "d3o:hasEnzyme",
                object: "entity_3",
            },
        ],
    };

    const state = new AnnotationState(JSON.stringify(annotationData));

    // Initial state: 3 entities, 2 relations
    expect(state.entities.size).toBe(3);
    expect(state.relations.size).toBe(2);

    // Simulate deleting entity_2 (which is referenced in both relations)
    // Using the same approach as deleteEntity() function

    // First delete its pointers
    let updatedPointers = state.pointers;
    state.pointers.forEach((pointer) => {
        if (pointer.entity_id === "entity_2") {
            updatedPointers = updatedPointers.delete(pointer.pointer_id);
        }
    });
    state.pointers = updatedPointers;

    // Delete relations that reference entity_2
    // Convert to array, filter, then create new Set (same as deleteEntity)
    const relationsArray = state.relations.toArray();
    const filteredRelations = relationsArray.filter(
        (relation) => relation.subject !== "entity_2" && relation.object !== "entity_2"
    );
    state.relations = Set(filteredRelations);

    // Delete the entity
    state.entities = state.entities.delete("entity_2");

    // After deletion: 2 entities, 0 relations
    // (both relations referenced entity_2)
    expect(state.entities.size).toBe(2);
    expect(state.relations.size).toBe(0);
    expect(state.entity("entity_2")).toBeUndefined();

    // entity_1 and entity_3 should still exist
    expect(state.entity("entity_1")).toBeDefined();
    expect(state.entity("entity_3")).toBeDefined();
});
