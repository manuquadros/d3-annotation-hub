import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const POST: RequestHandler = async ({ cookies, request }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const body = await request.formData();
    return fetch(`${API_BASE_URL}/admin/ontology/peek`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body,
    });
};
