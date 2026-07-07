import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => {
    const q = event.url.searchParams.get("q");
    if (!q) return new Response("Missing q", { status: 400 });

    return proxy(event, "/entity/search", {
        query: {
            q,
            limit: event.url.searchParams.get("limit"),
            project_id: event.url.searchParams.get("project_id"),
        },
    });
};
