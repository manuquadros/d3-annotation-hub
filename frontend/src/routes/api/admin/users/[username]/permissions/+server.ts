import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const PUT: RequestHandler = async (event) =>
    proxy(
        event,
        backendPath`/admin/users/${event.params.username!}/permissions`,
        {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: await event.request.text(),
        },
    );
