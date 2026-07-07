import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => proxy(event, "/projects");

export const POST: RequestHandler = async (event) =>
    proxy(event, "/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await event.request.text(),
    });
