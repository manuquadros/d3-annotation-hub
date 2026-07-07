import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => proxy(event, "/me/last-project");

export const PUT: RequestHandler = (event) => {
    const projectId = event.url.searchParams.get("project_id");
    if (!projectId) return new Response("project_id required", { status: 422 });

    return proxy(event, "/me/last-project", {
        method: "PUT",
        query: { project_id: projectId },
    });
};
