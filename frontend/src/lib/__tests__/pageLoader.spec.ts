import { describe, it, expect, vi, afterEach } from "vitest";
import { SaveSequencer } from "$lib/utils/saveSequencer";
import { loadSequencedPage } from "$lib/utils/pageLoader";

function jsonResponse(body: unknown, ok = true): Response {
    return { ok, json: async () => body } as unknown as Response;
}

afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
});

describe("loadSequencedPage", () => {
    it("returns the parsed body for the latest request", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(jsonResponse({ items: [1], total: 1 })),
        );
        const seq = new SaveSequencer();

        const r = await loadSequencedPage<{ items: number[]; total: number }>(
            seq,
            "/page",
        );

        expect(r).toEqual({ status: "ok", data: { items: [1], total: 1 } });
    });

    it("passes the sequencer's abort signal to fetch", async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
        vi.stubGlobal("fetch", fetchMock);

        await loadSequencedPage(new SaveSequencer(), "/page");

        expect(fetchMock.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
    });

    it("reports a non-OK response as error", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(jsonResponse({}, false)),
        );

        expect(await loadSequencedPage(new SaveSequencer(), "/page")).toEqual({
            status: "error",
        });
    });

    it("treats an aborted fetch as superseded, not an error", async () => {
        const aborted = new Error("aborted");
        aborted.name = "AbortError";
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue(aborted));

        expect(await loadSequencedPage(new SaveSequencer(), "/page")).toEqual({
            status: "superseded",
        });
    });

    it("reports an unexpected fetch failure as error", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockRejectedValue(new Error("network down")),
        );

        expect(await loadSequencedPage(new SaveSequencer(), "/page")).toEqual({
            status: "error",
        });
    });

    it("discards a response that a newer load superseded before parsing", async () => {
        const seq = new SaveSequencer();
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
                ok: true,
                json: async () => {
                    seq.begin(); // a newer request claims the sequencer mid-parse
                    return { items: [], total: 0 };
                },
            } as unknown as Response),
        );

        expect(await loadSequencedPage(seq, "/page")).toEqual({
            status: "superseded",
        });
    });

    it("keeps the latest of two overlapping loads and abandons the earlier", async () => {
        const seq = new SaveSequencer();
        let resolveEarlier!: (r: Response) => void;
        const earlierFetch = new Promise<Response>((res) => {
            resolveEarlier = res;
        });
        vi.stubGlobal(
            "fetch",
            vi
                .fn()
                .mockReturnValueOnce(earlierFetch)
                .mockResolvedValueOnce(jsonResponse({ total: 2 })),
        );

        const earlier = loadSequencedPage<{ total: number }>(seq, "/earlier");
        const later = await loadSequencedPage<{ total: number }>(seq, "/later");
        resolveEarlier(jsonResponse({ total: 1 })); // earlier finally responds, too late

        expect(later).toEqual({ status: "ok", data: { total: 2 } });
        expect(await earlier).toEqual({ status: "superseded" });
    });
});
