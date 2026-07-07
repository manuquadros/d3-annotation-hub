import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const POST: RequestHandler = (event) =>
    proxy(
        event,
        backendPath`/projects/${event.params.id!}/ontologies/${event.params.ontologyId!}`,
        { method: "POST" },
    );

export const DELETE: RequestHandler = (event) =>
    proxy(
        event,
        backendPath`/projects/${event.params.id!}/ontologies/${event.params.ontologyId!}`,
        { method: "DELETE" },
    );
