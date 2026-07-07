import { afterEach, describe, expect, it, vi } from "vitest";
import type { RequestEvent } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import { backendPath, proxy } from "$lib/server/proxy";

describe("backendPath", () => {
    it("leaves literal parts and their slashes untouched", () => {
        expect(backendPath`/projects/${1}/queue`).toBe("/projects/1/queue");
    });

    it("percent-encodes interpolated segments", () => {
        expect(backendPath`/projects/${"a b"}/x`).toBe("/projects/a%20b/x");
    });

    it("encodes slashes and dot-segments so a param cannot cross path boundaries", () => {
        // The TICKET-21 repro: a proposed-entity curie of `../ontologies/5`
        // must not resolve to the delete-ontology endpoint.
        const smuggled = backendPath`/admin/entities/${"../ontologies/5"}`;
        expect(smuggled).toBe("/admin/entities/..%2Fontologies%2F5");
        expect(smuggled).not.toContain("/ontologies/");
    });

    it("encodes an already-encoded slash so it cannot decode back to a real slash", () => {
        expect(backendPath`/x/${"a%2Fb"}`).toBe("/x/a%252Fb");
    });
});

function makeEvent(
    token: string | undefined,
    urlStr = "http://localhost/api/x",
): RequestEvent {
    return {
        cookies: {
            get: (name: string) => (name === "auth_token" ? token : undefined),
        },
        url: new URL(urlStr),
        params: {},
        request: new Request(urlStr),
    } as unknown as RequestEvent;
}

describe("proxy", () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        vi.restoreAllMocks();
    });

    it("returns 401 without calling the backend when the cookie is absent", async () => {
        const fetchMock = vi.fn();
        vi.stubGlobal("fetch", fetchMock);

        const res = await proxy(makeEvent(undefined), "/projects");

        expect(res.status).toBe(401);
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it("attaches the Bearer token and builds an encoded query, dropping null/undefined", async () => {
        const fetchMock = vi.fn().mockResolvedValue(new Response("ok"));
        vi.stubGlobal("fetch", fetchMock);

        await proxy(makeEvent("tok"), "/entity/search", {
            query: { q: "a b", limit: null, project_id: undefined, page: 3 },
        });

        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe(`${API_BASE_URL}/entity/search?q=a+b&page=3`);
        expect((init.headers as Record<string, string>).Authorization).toBe(
            "Bearer tok",
        );
    });

    it("preserves the upstream status/body but strips set-cookie and content-length", async () => {
        const upstream = new Response("payload", {
            status: 207,
            headers: {
                "content-type": "application/json",
                "content-length": "7",
                "set-cookie": "session=leak",
            },
        });
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue(upstream));

        const res = await proxy(makeEvent("tok"), "/x");

        expect(res.status).toBe(207);
        expect(await res.text()).toBe("payload");
        expect(res.headers.get("content-type")).toBe("application/json");
        expect(res.headers.get("set-cookie")).toBeNull();
        expect(res.headers.get("content-length")).toBeNull();
    });

    it("maps an aborted upstream (timeout) to 504", async () => {
        const abortErr = Object.assign(new Error("aborted"), {
            name: "AbortError",
        });
        vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abortErr));

        const res = await proxy(makeEvent("tok"), "/x");

        expect(res.status).toBe(504);
    });

    it("maps a failed upstream connection to 502", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockRejectedValue(new Error("ECONNREFUSED")),
        );

        const res = await proxy(makeEvent("tok"), "/x");

        expect(res.status).toBe(502);
    });
});
