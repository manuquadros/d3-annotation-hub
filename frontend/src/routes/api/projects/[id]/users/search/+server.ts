import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) =>
    proxy(event, backendPath`/projects/${event.params.id!}/users/search`, {
        query: { q: event.url.searchParams.get("q") ?? "" },
    });
