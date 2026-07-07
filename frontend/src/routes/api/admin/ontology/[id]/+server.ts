import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => {
    const p = event.url.searchParams;
    return proxy(
        event,
        backendPath`/admin/ontologies/${event.params.id!}/entities`,
        {
            query: {
                limit: p.get("limit") ?? "50",
                offset: p.get("offset") ?? "0",
                curie_filter: p.get("curie_filter") ?? "",
                name_filter: p.get("name_filter") ?? "",
                type_filter: p.get("type_filter") ?? "",
            },
        },
    );
};

export const DELETE: RequestHandler = (event) =>
    proxy(event, backendPath`/admin/ontologies/${event.params.id!}`, {
        method: "DELETE",
    });
