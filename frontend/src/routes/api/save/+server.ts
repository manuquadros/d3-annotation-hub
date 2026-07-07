import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const POST: RequestHandler = async (event) =>
    proxy(event, "/save/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: await event.request.text(),
    });
