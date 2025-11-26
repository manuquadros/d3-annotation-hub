import { render } from "@testing-library/svelte";
import { expect, test } from "vitest";
import Annotation from "$lib/components/Annotation.svelte";
import { AnnotationState } from "$lib/annotation.svelte";
import { Map, Set } from "immutable";

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
