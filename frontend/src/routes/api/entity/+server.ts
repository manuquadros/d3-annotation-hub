import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const q = url.searchParams.get("q");
    if (!q) return new Response("Missing q", { status: 400 });

    const params = new URLSearchParams({ q });
    const limit = url.searchParams.get("limit");
    if (limit) params.set("limit", limit);
    const projectId = url.searchParams.get("project_id");
    if (projectId) params.set("project_id", projectId);

    return fetch(`${API_BASE_URL}/entity/search?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
};
