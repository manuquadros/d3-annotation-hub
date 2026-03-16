import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    return fetch(`${API_BASE_URL}/admin/ontologies`, {
        headers: { Authorization: `Bearer ${token}` },
    });
};

export const POST: RequestHandler = async ({ cookies, request }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    // Forward the multipart form data as-is
    const body = await request.formData();
    return fetch(`${API_BASE_URL}/admin/ontology/import`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body,
    });
};
