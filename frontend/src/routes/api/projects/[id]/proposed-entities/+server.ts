import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies, params, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const limit = url.searchParams.get("limit") ?? "50";
    const offset = url.searchParams.get("offset") ?? "0";
    return fetch(
        `${API_BASE_URL}/projects/${params.id}/proposed-entities?limit=${limit}&offset=${offset}`,
        { headers: { Authorization: `Bearer ${token}` } },
    );
};

export const POST: RequestHandler = async ({ cookies, params, request }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const body = await request.json();
    return fetch(`${API_BASE_URL}/projects/${params.id}/proposed-entities`, {
        method: "POST",
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
};
