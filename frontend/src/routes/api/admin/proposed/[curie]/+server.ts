import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const DELETE: RequestHandler = (event) =>
    proxy(event, backendPath`/admin/entities/${event.params.curie!}`, {
        method: "DELETE",
    });

export const POST: RequestHandler = (event) => {
    const action = event.url.searchParams.get("action");
    if (action === "confirm") {
        return proxy(
            event,
            backendPath`/admin/entities/${event.params.curie!}/confirm`,
            { method: "POST" },
        );
    }
    return new Response("Unknown action", { status: 400 });
};

export const PATCH: RequestHandler = async (event) =>
    proxy(event, backendPath`/admin/entities/${event.params.curie!}/curie`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: await event.request.text(),
    });
