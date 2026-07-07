import type { RequestHandler } from "@sveltejs/kit";
import { backendPath, proxy } from "$lib/server/proxy";

export const GET: RequestHandler = (event) => {
    const email = event.url.searchParams.get("email");
    if (!email) return new Response("Missing email", { status: 400 });

    return proxy(
        event,
        backendPath`/projects/${event.params.id!}/members/lookup`,
        { query: { email } },
    );
};
