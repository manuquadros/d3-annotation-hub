import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const DELETE: RequestHandler = async ({ params, cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(`${API_BASE_URL}/admin/entities/${params.curie}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });
};

export const POST: RequestHandler = async ({ params, url, cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const action = url.searchParams.get("action");
    if (action === "confirm") {
        return fetch(`${API_BASE_URL}/admin/entities/${params.curie}/confirm`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}` },
        });
    }

    return new Response("Unknown action", { status: 400 });
};

export const PATCH: RequestHandler = async ({ params, request, cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const body = await request.json();
    return fetch(`${API_BASE_URL}/admin/entities/${params.curie}/curie`, {
        method: "PATCH",
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
    });
};
