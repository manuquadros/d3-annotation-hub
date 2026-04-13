import { error } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ cookies, params, parent }) => {
    const { isAdmin } = await parent();
    if (!isAdmin) error(403, "Access required");

    const token = cookies.get("auth_token")!;
    const res = await fetch(`${API_BASE_URL}/projects/${params.id}/members`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const members = res.ok ? await res.json() : [];
    return { projectId: Number(params.id), members };
};
