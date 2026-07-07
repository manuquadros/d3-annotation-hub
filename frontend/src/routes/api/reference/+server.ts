import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => {
    const refIdentifier = event.url.searchParams.get("ref_identifier");
    if (!refIdentifier) {
        return new Response("Missing ref_identifier", { status: 400 });
    }

    const projectId = event.url.searchParams.get("project_id");
    if (!projectId) {
        return new Response("Missing project_id", { status: 400 });
    }

    return proxy(event, "/reference/", {
        query: { ref_identifier: refIdentifier, project_id: projectId },
    });
};
