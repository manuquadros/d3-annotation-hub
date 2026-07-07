import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => proxy(event, "/admin/users");

export const POST: RequestHandler = async (event) =>
    proxy(event, "/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await event.request.text(),
    });
