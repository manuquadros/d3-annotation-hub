import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ cookies, url }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const projectId = url.searchParams.get("project_id");
    if (!projectId) return new Response(null, { status: 400 });

    return fetch(
        `${API_BASE_URL}/me/project-roles?project_id=${encodeURIComponent(projectId)}`,
        { headers: { Authorization: `Bearer ${token}` } },
    );
};
