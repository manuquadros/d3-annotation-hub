import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const PUT: RequestHandler = async ({ cookies, params, request }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(
        `${API_BASE_URL}/admin/users/${encodeURIComponent(params.username!)}/permissions`,
        {
            method: "PUT",
            headers: {
                Authorization: `Bearer ${token}`,
                "Content-Type": "application/json",
            },
            body: await request.text(),
        },
    );
};
