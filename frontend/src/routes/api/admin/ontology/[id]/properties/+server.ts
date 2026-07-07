import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) =>
    proxy(event, backendPath`/admin/ontologies/${event.params.id!}/properties`);
