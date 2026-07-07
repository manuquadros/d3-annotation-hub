import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) =>
    proxy(event, backendPath`/projects/${event.params.id!}/references`);

export const POST: RequestHandler = async (event) =>
    proxy(event, backendPath`/projects/${event.params.id!}/references`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await event.request.text(),
    });
