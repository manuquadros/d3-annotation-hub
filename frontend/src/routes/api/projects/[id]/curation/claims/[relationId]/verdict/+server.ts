import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const POST: RequestHandler = async (event) =>
    proxy(
        event,
        backendPath`/projects/${event.params.id!}/curation/claims/${event.params.relationId!}/verdict`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: await event.request.text(),
        },
    );
