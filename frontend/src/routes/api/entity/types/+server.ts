import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) =>
    proxy(event, "/entity/types", {
        query: { q: event.url.searchParams.get("q") ?? "" },
    });
