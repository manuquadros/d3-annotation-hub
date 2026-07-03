import { describe, it, expect } from "vitest";
import { errorDetail } from "$lib/utils/http";

describe("errorDetail", () => {
    it("prefers the JSON detail field", async () => {
        const res = new Response(JSON.stringify({ detail: "already in use" }), {
            status: 409,
        });
        expect(await errorDetail(res)).toBe("already in use");
    });

    it("falls back to raw text for a non-JSON body", async () => {
        const res = new Response("<html>502 Bad Gateway</html>", {
            status: 502,
        });
        expect(await errorDetail(res)).toBe("<html>502 Bad Gateway</html>");
    });

    it("falls back to raw text for JSON without a detail field", async () => {
        const res = new Response(JSON.stringify({ message: "nope" }), {
            status: 400,
        });
        expect(await errorDetail(res)).toBe('{"message":"nope"}');
    });

    it("uses the status line when the body is empty", async () => {
        const res = new Response("", {
            status: 503,
            statusText: "Service Unavailable",
        });
        expect(await errorDetail(res)).toBe("Service Unavailable");
    });

    it("falls back to the status code when body and statusText are empty", async () => {
        const res = new Response("", { status: 500, statusText: "" });
        expect(await errorDetail(res)).toBe("Request failed (500)");
    });
});
