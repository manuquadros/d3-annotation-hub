import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) =>
    proxy(event, "/admin/entities/proposed", {
        query: {
            limit: event.url.searchParams.get("limit") ?? "50",
            offset: event.url.searchParams.get("offset") ?? "0",
        },
    });
