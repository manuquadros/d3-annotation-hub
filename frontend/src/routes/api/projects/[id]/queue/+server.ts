import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) =>
    proxy(event, backendPath`/projects/${event.params.id!}/queue`);

export const POST: RequestHandler = (event) => {
    const ref = event.url.searchParams.get("ref");
    if (!ref) return new Response("Missing ref", { status: 400 });

    return proxy(
        event,
        backendPath`/projects/${event.params.id!}/queue/complete`,
        { method: "POST", query: { ref } },
    );
};

export const DELETE: RequestHandler = (event) => {
    const ref = event.url.searchParams.get("ref");
    if (!ref) return new Response("Missing ref", { status: 400 });

    return proxy(
        event,
        backendPath`/projects/${event.params.id!}/queue/complete`,
        { method: "DELETE", query: { ref } },
    );
};
