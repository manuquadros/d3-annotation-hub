import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies, params, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const email = url.searchParams.get("email");
    if (!email) return new Response("Missing email", { status: 400 });

    return fetch(
        `${API_BASE_URL}/projects/${params.id}/members/lookup?email=${encodeURIComponent(email)}`,
        { headers: { Authorization: `Bearer ${token}` } },
    );
};
