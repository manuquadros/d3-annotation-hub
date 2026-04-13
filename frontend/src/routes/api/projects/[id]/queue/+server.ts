import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies, params }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(`${API_BASE_URL}/projects/${params.id}/queue`, {
        headers: { Authorization: `Bearer ${token}` },
    });
};

export const POST: RequestHandler = async ({ cookies, params, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const ref = url.searchParams.get("ref");
    if (!ref) return new Response("Missing ref", { status: 400 });

    return fetch(
        `${API_BASE_URL}/projects/${params.id}/queue/complete?ref=${encodeURIComponent(ref)}`,
        {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        },
    );
};

export const DELETE: RequestHandler = async ({ cookies, params, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const ref = url.searchParams.get("ref");
    if (!ref) return new Response("Missing ref", { status: 400 });

    return fetch(
        `${API_BASE_URL}/projects/${params.id}/queue/complete?ref=${encodeURIComponent(ref)}`,
        {
            method: "DELETE",
            headers: { Authorization: `Bearer ${token}` },
        },
    );
};
