import { error } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ cookies, params, parent }) => {
    const { isAdmin } = await parent();
    if (!isAdmin) error(403, "Access required");

    const token = cookies.get("auth_token")!;
    const headers = { Authorization: `Bearer ${token}` };
    const projectId = Number(params.id);

    const [projectOntologiesRes, allOntologiesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/projects/${projectId}/ontologies`, { headers }),
        fetch(`${API_BASE_URL}/admin/ontologies`, { headers }),
    ]);

    const projectOntologies = projectOntologiesRes.ok
        ? await projectOntologiesRes.json()
        : [];
    const allOntologies = allOntologiesRes.ok
        ? await allOntologiesRes.json()
        : [];

    return { projectId, projectOntologies, allOntologies };
};
