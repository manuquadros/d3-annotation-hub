import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const POST: RequestHandler = async (event) =>
    proxy(event, "/admin/ontology/peek", {
        method: "POST",
        body: await event.request.formData(),
    });
