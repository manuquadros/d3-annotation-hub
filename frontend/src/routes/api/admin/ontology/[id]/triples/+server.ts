import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => {
    const p = event.url.searchParams;
    return proxy(
        event,
        backendPath`/admin/ontologies/${event.params.id!}/triples`,
        {
            query: {
                limit: p.get("limit") ?? "50",
                offset: p.get("offset") ?? "0",
                subject_filter: p.get("subject_filter") ?? "",
                predicate_filter: p.get("predicate_filter") ?? "",
                object_filter: p.get("object_filter") ?? "",
            },
        },
    );
};
