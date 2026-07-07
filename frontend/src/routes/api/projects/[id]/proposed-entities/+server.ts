import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) =>
    proxy(event, backendPath`/projects/${event.params.id!}/proposed-entities`, {
        query: {
            limit: event.url.searchParams.get("limit") ?? "50",
            offset: event.url.searchParams.get("offset") ?? "0",
        },
    });

export const POST: RequestHandler = async (event) =>
    proxy(event, backendPath`/projects/${event.params.id!}/proposed-entities`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await event.request.text(),
    });
