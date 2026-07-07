import type { RequestHandler } from "@sveltejs/kit";
import { proxy } from "$lib/server/proxy";

export const POST: RequestHandler = (event) =>
    proxy(event, "/admin/fts/rebuild", { method: "POST" });
