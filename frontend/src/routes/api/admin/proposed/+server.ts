import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ url, cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const params = new URLSearchParams({
        limit: url.searchParams.get("limit") ?? "50",
        offset: url.searchParams.get("offset") ?? "0",
    });

    return fetch(`${API_BASE_URL}/admin/entities/proposed?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
};
