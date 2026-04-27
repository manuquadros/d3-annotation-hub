import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const PATCH: RequestHandler = async ({
    cookies,
    params,
    url,
    request,
}) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const curie = url.searchParams.get("curie");
    if (!curie) return new Response("Missing curie", { status: 400 });

    return fetch(
        `${API_BASE_URL}/projects/${params.id}/curation/entity-curie?curie=${encodeURIComponent(curie)}`,
        {
            method: "PATCH",
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
            },
            body: await request.text(),
        },
    );
};
