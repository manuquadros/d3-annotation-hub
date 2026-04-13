import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const POST: RequestHandler = async ({ cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(`${API_BASE_URL}/admin/fts/rebuild`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
    });
};
