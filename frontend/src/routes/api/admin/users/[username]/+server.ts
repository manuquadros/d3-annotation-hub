import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const DELETE: RequestHandler = (event) =>
    proxy(event, backendPath`/admin/users/${event.params.username!}`, {
        method: "DELETE",
    });
