import { afterEach, describe, expect, it, vi } from "vitest";
import type { RequestEvent } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";

import { DELETE as proposedDelete } from "../../routes/api/admin/proposed/[curie]/+server";
import { POST as queueComplete } from "../../routes/api/projects/[id]/queue/+server";
import { GET as entitySearch } from "../../routes/api/entity/+server";
import { PUT as lastProject } from "../../routes/api/me/last-project/+server";
import { DELETE as memberRole } from "../../routes/api/projects/[id]/members/[userId]/[role]/+server";

function ev(params: Record<string, string>, urlStr: string): RequestEvent {
    return {
        cookies: { get: () => "tok" },
        params,
        url: new URL(urlStr),
        request: new Request(urlStr),
    } as unknown as RequestEvent;
}

describe("migrated route wiring", () => {
    let lastCall: [string, RequestInit];
    afterEach(() => vi.unstubAllGlobals());

    function stub() {
        vi.stubGlobal(
            "fetch",
            vi.fn((url: string, init: RequestInit) => {
                lastCall = [url, init];
                return Promise.resolve(new Response("ok"));
            }),
        );
    }

    it("proposed-entity DELETE cannot cross into the ontologies endpoint (TICKET-21 repro)", async () => {
        stub();
        await proposedDelete(
            ev(
                { curie: "../ontologies/5" },
                "http://localhost/api/admin/proposed/x",
            ),
        );
        expect(lastCall[0]).toBe(
            `${API_BASE_URL}/admin/entities/..%2Fontologies%2F5`,
        );
        expect(lastCall[1].method).toBe("DELETE");
    });

    it("queue complete POST targets the complete sub-path with an encoded ref", async () => {
        stub();
        await queueComplete(
            ev({ id: "7" }, "http://localhost/api/projects/7/queue?ref=PMC 1"),
        );
        expect(lastCall[0]).toBe(
            `${API_BASE_URL}/projects/7/queue/complete?ref=PMC+1`,
        );
        expect(lastCall[1].method).toBe("POST");
    });

    it("entity search forwards q to /entity/search", async () => {
        stub();
        await entitySearch(
            ev({}, "http://localhost/api/entity?q=coli&limit=5"),
        );
        expect(lastCall[0]).toBe(
            `${API_BASE_URL}/entity/search?q=coli&limit=5`,
        );
    });

    it("last-project PUT encodes project_id in the query", async () => {
        stub();
        await lastProject(
            ev({}, "http://localhost/api/me/last-project?project_id=a/b"),
        );
        expect(lastCall[0]).toBe(
            `${API_BASE_URL}/me/last-project?project_id=a%2Fb`,
        );
        expect(lastCall[1].method).toBe("PUT");
    });

    it("member-role DELETE encodes every path param", async () => {
        stub();
        await memberRole(
            ev(
                { id: "1", userId: "u/2", role: "curator" },
                "http://localhost/api/projects/1/members/u/2/curator",
            ),
        );
        expect(lastCall[0]).toBe(
            `${API_BASE_URL}/projects/1/members/u%2F2/curator`,
        );
        expect(lastCall[1].method).toBe("DELETE");
    });
});
