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

function makeSseStream(
    events: Array<{ event: string; data: object }>,
): Response {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
        start(controller) {
            for (const { event, data } of events) {
                controller.enqueue(
                    encoder.encode(
                        `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`,
                    ),
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

/** An SSE stream whose events are pushed manually, so a test can inspect the
 *  DOM mid-import before the stream closes. */
function makeControlledSseStream(): {
    response: Response;
    push: (event: string, data: object) => void;
    close: () => void;
} {
    const encoder = new TextEncoder();
    let ctrl!: ReadableStreamDefaultController;
    const body = new ReadableStream({
        start(controller) {
            ctrl = controller;
        },
    });
    return {
        response: new Response(body, {
            status: 200,
            headers: { "Content-Type": "text/event-stream" },
        }),
        push: (event, data) =>
            ctrl.enqueue(
                encoder.encode(
                    `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`,
                ),
            ),
        close: () => ctrl.close(),
    };
}

beforeEach(() => {
    vi.restoreAllMocks();
});

function peekResponse(meta: {
    name?: string | null;
    prefix?: string | null;
    base_iri?: string | null;
    version?: string | null;
}): Response {
    return new Response(
        JSON.stringify({
            name: null,
            prefix: null,
            base_iri: null,
            version: null,
            ...meta,
        }),
        { status: 200 },
    );
}

function selectFile(fileInput: HTMLInputElement, file: File): Promise<boolean> {
    Object.defineProperty(fileInput, "files", {
        value: [file],
        configurable: true,
    });
    return fireEvent.change(fileInput);
}

describe("OntologyImportForm — peek auto-fill", () => {
    test("typing in the name field prevents a later peek response from overwriting it", async () => {
        let resolvePeek!: (r: Response) => void;
        vi.spyOn(globalThis, "fetch").mockImplementation(
            () =>
                new Promise<Response>((r) => {
                    resolvePeek = r;
                }),
        );

        const { getByLabelText, container } = render(OntologyImportForm);
        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        const fileInput = container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;

        // File selected — name auto-set from filename, peek in-flight
        await selectFile(fileInput, new File([""], "myfile.owl"));
        expect(nameInput.value).toBe("myfile");

        // User types before peek resolves
        await fireEvent.input(nameInput, {
            target: { value: "My Typed Name" },
        });

        // Peek resolves with a different label
        resolvePeek(peekResponse({ name: "OWL Ontology Label" }));
        await new Promise((r) => setTimeout(r, 0));

        expect(nameInput.value).toBe("My Typed Name");
    });

    test("nameAutoSet is reset when file input is cleared, preventing stale overwrite on next selection", async () => {
        let resolveFirst!: (r: Response) => void;
        let resolveSecond!: (r: Response) => void;
        vi.spyOn(globalThis, "fetch")
            .mockImplementationOnce(
                () =>
                    new Promise<Response>((r) => {
                        resolveFirst = r;
                    }),
            )
            .mockImplementationOnce(
                () =>
                    new Promise<Response>((r) => {
                        resolveSecond = r;
                    }),
            );

        const { getByLabelText, container } = render(OntologyImportForm);
        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        const fileInput = container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;

        // Select file A — name auto-set, nameAutoSet=true
        await selectFile(fileInput, new File([""], "file-a.owl"));

        // Peek A resolves with no name — nameAutoSet stays true without the V2 fix
        resolveFirst(peekResponse({ name: null }));
        await new Promise((r) => setTimeout(r, 0));

        // User clears the file
        Object.defineProperty(fileInput, "files", {
            value: [],
            configurable: true,
        });
        await fireEvent.change(fileInput);
        // After fix: autoFilled cleared here, so peek can no longer override user input

        // User types a name (would not reset nameAutoSet if file clear didn't)
        await fireEvent.input(nameInput, {
            target: { value: "My Custom Name" },
        });

        // Select file B — peek resolves with a label
        await selectFile(fileInput, new File([""], "file-b.owl"));
        resolveSecond(peekResponse({ name: "B Ontology Label" }));
        await new Promise((r) => setTimeout(r, 0));

        // User's typed name must not be overwritten
        expect(nameInput.value).toBe("My Custom Name");
    });

    test("re-selecting a file repopulates auto-filled fields but preserves user-typed fields", async () => {
        let resolveA!: (r: Response) => void;
        let resolveB!: (r: Response) => void;
        vi.spyOn(globalThis, "fetch")
            .mockImplementationOnce(
                () =>
                    new Promise<Response>((r) => {
                        resolveA = r;
                    }),
            )
            .mockImplementationOnce(
                () =>
                    new Promise<Response>((r) => {
                        resolveB = r;
                    }),
            );

        const { getByLabelText, container } = render(OntologyImportForm);
        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        const prefixInput = getByLabelText(/prefix/i) as HTMLInputElement;
        const fileInput = container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;

        // Select file A — peek fills name and prefix
        await selectFile(fileInput, new File([""], "file-a.owl"));
        resolveA(peekResponse({ name: "A Ontology", prefix: "A_PREFIX" }));
        await new Promise((r) => setTimeout(r, 0));
        expect(nameInput.value).toBe("A Ontology");
        expect(prefixInput.value).toBe("A_PREFIX");

        // User edits prefix — locks that field against future auto-fill
        await fireEvent.input(prefixInput, { target: { value: "MY_PREFIX" } });

        // Select file B without clearing first
        await selectFile(fileInput, new File([""], "file-b.owl"));
        resolveB(peekResponse({ name: "B Ontology", prefix: "B_PREFIX" }));
        await new Promise((r) => setTimeout(r, 0));

        // Auto-filled name was cleared and repopulated from file B
        expect(nameInput.value).toBe("B Ontology");
        // User-typed prefix was not touched
        expect(prefixInput.value).toBe("MY_PREFIX");
    });

    test("stale peek response from a previously selected file is discarded", async () => {
        let resolveA!: (r: Response) => void;
        let resolveB!: (r: Response) => void;
        vi.spyOn(globalThis, "fetch")
            .mockImplementationOnce(
                () =>
                    new Promise<Response>((r) => {
                        resolveA = r;
                    }),
            )
            .mockImplementationOnce(
                () =>
                    new Promise<Response>((r) => {
                        resolveB = r;
                    }),
            );

        const { getByLabelText, container } = render(OntologyImportForm);
        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        const prefixInput = getByLabelText(/prefix/i) as HTMLInputElement;
        const fileInput = container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;

        // Select file A — peek A starts (slow)
        await selectFile(fileInput, new File([""], "file-a.owl"));

        // Select file B before A resolves — peek B starts, peekSeq incremented
        await selectFile(fileInput, new File([""], "file-b.owl"));

        // B resolves first: name "B Ontology", no prefix
        resolveB(peekResponse({ name: "B Ontology", prefix: null }));
        await new Promise((r) => setTimeout(r, 0));
        expect(nameInput.value).toBe("B Ontology");

        // A resolves late: tries to set a different name and a prefix
        resolveA(peekResponse({ name: "A Ontology", prefix: "A_PREFIX" }));
        await new Promise((r) => setTimeout(r, 0));

        // Stale response must have been ignored entirely
        expect(nameInput.value).toBe("B Ontology");
        expect(prefixInput.value).toBe(""); // A's prefix not applied
    });
});

describe("OntologyImportForm — callback error handling", () => {
    test("form fields are retained when onimported throws", async () => {
        vi.spyOn(globalThis, "fetch")
            .mockResolvedValueOnce(peekResponse({})) // peek on file select
            .mockResolvedValueOnce(makeSseStream([COMPLETE_EVENT]));

        const onimported = vi
            .fn()
            .mockRejectedValue(new Error("Assign failed"));

        const { getByLabelText, findByText, container } = render(
            OntologyImportForm,
            {
                props: { onimported },
            },
        );

        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        const prefixInput = getByLabelText(/prefix/i) as HTMLInputElement;
        const fileInput = container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;

        await fireEvent.input(nameInput, {
            target: { value: "Test Ontology" },
        });
        await fireEvent.input(prefixInput, { target: { value: "TEST" } });

        const file = new File(["content"], "test.owl", {
            type: "application/rdf+xml",
        });
        Object.defineProperty(fileInput, "files", {
            value: [file],
            configurable: true,
        });
        await fireEvent.change(fileInput);

        await fireEvent.submit(container.querySelector("form")!);

        await findByText("Assign failed");

        expect(nameInput.value).toBe("Test Ontology");
        expect(prefixInput.value).toBe("TEST");
        expect(fileInput.files?.[0]?.name).toBe("test.owl");
    });

    test("error from onimported shows errorMessage", async () => {
        vi.spyOn(globalThis, "fetch")
            .mockResolvedValueOnce(peekResponse({}))
            .mockResolvedValueOnce(makeSseStream([COMPLETE_EVENT]));

        const onimported = vi.fn().mockRejectedValue(new Error("409 Conflict"));

        const { findByText, container } = render(OntologyImportForm, {
            props: { onimported },
        });

        const fileInput = container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;
        const file = new File(["content"], "test.owl", {
            type: "application/rdf+xml",
        });
        Object.defineProperty(fileInput, "files", {
            value: [file],
            configurable: true,
        });
        await fireEvent.change(fileInput);

        await fireEvent.submit(container.querySelector("form")!);

        await findByText("409 Conflict");
        expect(container.querySelector(".success")).toBeNull();
    });

    test("form fields are cleared after successful import when onimported resolves", async () => {
        vi.spyOn(globalThis, "fetch")
            .mockResolvedValueOnce(peekResponse({}))
            .mockResolvedValueOnce(makeSseStream([COMPLETE_EVENT]));

        const onimported = vi.fn().mockResolvedValue(undefined);

        const { getByLabelText, findByText, container } = render(
            OntologyImportForm,
            {
                props: { onimported },
            },
        );

        const nameInput = getByLabelText(/name/i) as HTMLInputElement;
        await fireEvent.input(nameInput, { target: { value: "My Ontology" } });

        const fileInput = container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;
        const file = new File(["content"], "test.owl", {
            type: "application/rdf+xml",
        });
        Object.defineProperty(fileInput, "files", {
            value: [file],
            configurable: true,
        });
        await fireEvent.change(fileInput);

        await fireEvent.submit(container.querySelector("form")!);

        await findByText(/imported 100 entities/i);
        expect(nameInput.value).toBe("");
    });
});

describe("OntologyImportForm — streaming progress (unknown totals)", () => {
    async function submitWith(response: Response) {
        vi.spyOn(globalThis, "fetch")
            .mockResolvedValueOnce(peekResponse({}))
            .mockResolvedValueOnce(response);

        const utils = render(OntologyImportForm);
        const fileInput = utils.container.querySelector(
            'input[type="file"]',
        ) as HTMLInputElement;
        const file = new File(["content"], "test.owl", {
            type: "application/rdf+xml",
        });
        Object.defineProperty(fileInput, "files", {
            value: [file],
            configurable: true,
        });
        await fireEvent.change(fileInput);
        await fireEvent.submit(utils.container.querySelector("form")!);
        return utils;
    }

    test("import completes when progress events carry total=0", async () => {
        const events = [
            { event: "progress", data: { step: "parse", loaded: 1, total: 1 } },
            {
                event: "progress",
                data: { step: "store_ontology", loaded: 1, total: 1 },
            },
            {
                event: "progress",
                data: { step: "load_entities", loaded: 500, total: 0 },
            },
            {
                event: "progress",
                data: { step: "load_triples", loaded: 200, total: 0 },
            },
            {
                event: "progress",
                data: { step: "load_properties", loaded: 5, total: 0 },
            },
            COMPLETE_EVENT,
        ];
        const { findByText } = await submitWith(makeSseStream(events));
        await findByText(/imported 100 entities/i);
    });

    test("shows the running loaded count while a total=0 step is active", async () => {
        const stream = makeControlledSseStream();
        const { findByText } = await submitWith(stream.response);

        stream.push("progress", { step: "parse", loaded: 1, total: 1 });
        stream.push("progress", {
            step: "load_entities",
            loaded: 12345,
            total: 0,
        });

        // The active entity step renders its running count (locale-formatted).
        await findByText("12,345");
        stream.close();
    });
});
