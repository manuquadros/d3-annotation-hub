import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies, params, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });
    const q = url.searchParams.get("q") ?? "";
    return fetch(
        `${API_BASE_URL}/projects/${params.id}/users/search?q=${encodeURIComponent(q)}`,
        { headers: { Authorization: `Bearer ${token}` } },
    );
};
