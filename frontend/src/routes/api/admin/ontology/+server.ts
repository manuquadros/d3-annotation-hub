import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => proxy(event, "/admin/ontologies");

export const POST: RequestHandler = async (event) =>
    // Streaming SSE import: forward the multipart body as-is and disable the
    // time-to-first-byte guard so a multi-minute upload/import isn't cut off.
    proxy(event, "/admin/ontology/import", {
        method: "POST",
        body: await event.request.formData(),
        timeoutMs: 0,
    });
