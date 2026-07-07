import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const POST: RequestHandler = async (event) =>
    proxy(event, "/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await event.request.text(),
    });
