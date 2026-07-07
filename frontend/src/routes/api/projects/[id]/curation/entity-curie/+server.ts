import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const PATCH: RequestHandler = async (event) => {
    const curie = event.url.searchParams.get("curie");
    if (!curie) return new Response("Missing curie", { status: 400 });

    return proxy(
        event,
        backendPath`/projects/${event.params.id!}/curation/entity-curie`,
        {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            query: { curie },
            body: await event.request.text(),
        },
    );
};
