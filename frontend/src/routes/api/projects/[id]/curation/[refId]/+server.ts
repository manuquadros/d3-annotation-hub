import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const POST: RequestHandler = async (event) =>
    proxy(
        event,
        backendPath`/projects/${event.params.id!}/curation/${event.params.refId!}`,
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: await event.request.text(),
        },
    );
