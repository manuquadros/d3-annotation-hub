import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => {
    const projectId = event.url.searchParams.get("project_id");
    if (!projectId) return new Response(null, { status: 400 });

    return proxy(event, "/me/project-roles", {
        query: { project_id: projectId },
    });
};
