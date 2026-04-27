import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(`${API_BASE_URL}/me/last-project`, {
        headers: { Authorization: `Bearer ${token}` },
    });
};

export const PUT: RequestHandler = async ({ cookies, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const projectId = url.searchParams.get("project_id");
    if (!projectId) return new Response("project_id required", { status: 422 });

    return fetch(`${API_BASE_URL}/me/last-project?project_id=${projectId}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` },
    });
};
