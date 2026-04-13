import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const refIdentifier = url.searchParams.get("ref_identifier");
    if (!refIdentifier) {
        return new Response("Missing ref_identifier", { status: 400 });
    }

    const projectId = url.searchParams.get("project_id");
    if (!projectId) {
        return new Response("Missing project_id", { status: 400 });
    }

    const params = new URLSearchParams({
        ref_identifier: refIdentifier,
        project_id: projectId,
    });

    return fetch(`${API_BASE_URL}/reference/?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
    });
};
