import { error } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import { canManageProject } from "$lib/utils/projectAccess";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ cookies, params, parent }) => {
    if (!canManageProject(await parent(), Number(params.id)))
        error(403, "Access required");

    const token = cookies.get("auth_token")!;
    const res = await fetch(
        `${API_BASE_URL}/projects/${params.id}/references`,
        {
            headers: { Authorization: `Bearer ${token}` },
        },
    );
    const references = res.ok ? await res.json() : [];
    return { projectId: Number(params.id), references };
};
