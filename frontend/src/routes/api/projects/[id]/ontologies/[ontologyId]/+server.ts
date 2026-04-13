import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const POST: RequestHandler = async ({ cookies, params }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(
        `${API_BASE_URL}/projects/${params.id}/ontologies/${params.ontologyId}`,
        {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        },
    );
};

export const DELETE: RequestHandler = async ({ cookies, params }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(
        `${API_BASE_URL}/projects/${params.id}/ontologies/${params.ontologyId}`,
        {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
        },
    );
};
