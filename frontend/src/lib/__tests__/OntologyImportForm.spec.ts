import { describe, test, expect, vi, beforeEach } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import { computeOverallPct, type ImportStep } from "$lib/utils/importProgress";
import OntologyImportForm from "$lib/components/OntologyImportForm.svelte";

function makeStep(
    step: string,
    status: ImportStep["status"],
    loaded = 0,
    total = 0,
    isBinary = false,
): ImportStep {
    return { step, label: step, status, counts: { loaded, total }, isBinary };
}

describe("computeOverallPct", () => {
    test("returns 0 for empty steps", () => {
        expect(computeOverallPct([])).toBe(0);
    });

    test("returns 0 when all steps are pending", () => {
        const steps = [
            makeStep("parse", "pending"),
            makeStep("load_entities", "pending"),
        ];
        expect(computeOverallPct(steps)).toBe(0);
    });

    test("returns 100 when all steps are done", () => {
        const steps = [
            makeStep("parse", "done", 1, 1, true),
            makeStep("store_ontology", "done", 1, 1, true),
            makeStep("load_entities", "done", 500, 500),
        ];
        expect(computeOverallPct(steps)).toBe(100);
    });

    test("interpolates partial progress for an active step", () => {
        // 1 done + 1 active at 50% out of 2 total = 75%
        const steps = [
            makeStep("parse", "done", 1, 1, true),
            makeStep("load_entities", "active", 250, 500),
        ];
        expect(computeOverallPct(steps)).toBe(75);
    });

    test("error steps contribute 0 to progress", () => {
        const steps = [
            makeStep("parse", "done", 1, 1, true),
            makeStep("load_entities", "error", 0, 500),
        ];
        expect(computeOverallPct(steps)).toBe(50);
    });

    test("active step with total=0 counts as complete (zero-total fix)", () => {
        // 4 done + 1 active with total=0 → should be 100%, not stalled at 80%
        const steps = [
            makeStep("parse", "done", 1, 1, true),
            makeStep("store_ontology", "done", 1, 1, true),
            makeStep("load_entities", "done", 10, 10),
            makeStep("load_triples", "done", 5, 5),
            makeStep("load_properties", "active", 0, 0),
        ];
        expect(computeOverallPct(steps)).toBe(100);
    });

    test("active step with total=0 does not stall mid-import", () => {
        // 2 done + 1 active zero-total + 2 pending = (2 + 1) / 5 = 60%
        const steps = [
            makeStep("parse", "done", 1, 1, true),
            makeStep("store_ontology", "done", 1, 1, true),
            makeStep("load_entities", "active", 0, 0),
            makeStep("load_triples", "pending"),
            makeStep("load_properties", "pending"),
        ];
        expect(computeOverallPct(steps)).toBe(60);
    });
});

function makeSseStream(events: Array<{ event: string; data: object }>): Response {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
        start(controller) {
            for (const { event, data } of events) {
                controller.enqueue(
                    encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`),
                );
            }
            controller.close();
        },
    });
    return new Response(body, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
    });
}

const COMPLETE_EVENT = {
    event: "complete",
    data: { ontology_id: 42, entities: 100, triples: 50, properties: 5 },
};

beforeEach(() => {
    vi.restoreAllMocks();
});

describe("OntologyImportForm — callback error handling", () => {
    test("form fields are retained when onimported throws", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
            makeSseStream([COMPLETE_EVENT]),
        );

        const onimported = vi.fn().mockRejectedValue(new Error("Assign failed"));

        const { getByLabelText, findByText, container } = render(OntologyImportForm, {
            props: { onimported },
        });

        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        const prefixInput = getByLabelText(/prefix/i) as HTMLInputElement;
        const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

        await fireEvent.input(nameInput, { target: { value: "Test Ontology" } });
        await fireEvent.input(prefixInput, { target: { value: "TEST" } });

        const file = new File(["content"], "test.owl", { type: "application/rdf+xml" });
        Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
        await fireEvent.change(fileInput);

        await fireEvent.submit(container.querySelector("form")!);

        await findByText("Assign failed");

        expect(nameInput.value).toBe("Test Ontology");
        expect(prefixInput.value).toBe("TEST");
        expect(fileInput.files?.[0]?.name).toBe("test.owl");
    });

    test("error from onimported shows errorMessage", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
            makeSseStream([COMPLETE_EVENT]),
        );

        const onimported = vi.fn().mockRejectedValue(new Error("409 Conflict"));

        const { findByText, container } = render(OntologyImportForm, { props: { onimported } });

        const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
        const file = new File(["content"], "test.owl", { type: "application/rdf+xml" });
        Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
        await fireEvent.change(fileInput);

        await fireEvent.submit(container.querySelector("form")!);

        await findByText("409 Conflict");
        expect(container.querySelector(".success")).toBeNull();
    });

    test("form fields are cleared after successful import when onimported resolves", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
            makeSseStream([COMPLETE_EVENT]),
        );

        const onimported = vi.fn().mockResolvedValue(undefined);

        const { getByLabelText, findByText, container } = render(OntologyImportForm, {
            props: { onimported },
        });

        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        await fireEvent.input(nameInput, { target: { value: "My Ontology" } });

        const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
        const file = new File(["content"], "test.owl", { type: "application/rdf+xml" });
        Object.defineProperty(fileInput, "files", { value: [file], configurable: true });
        await fireEvent.change(fileInput);

        await fireEvent.submit(container.querySelector("form")!);

        await findByText(/imported 100 entities/i);
        expect(nameInput.value).toBe("");
    });
});
