import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ params, url, cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const limit = url.searchParams.get("limit") ?? "50";
    const offset = url.searchParams.get("offset") ?? "0";
    return fetch(
        `${API_BASE_URL}/admin/ontologies/${params.id}/entities?limit=${limit}&offset=${offset}`,
        { headers: { Authorization: `Bearer ${token}` } },
    );
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(`${API_BASE_URL}/admin/ontologies/${params.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });
};
