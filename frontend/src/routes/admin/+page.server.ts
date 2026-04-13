import { error, redirect } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) redirect(302, "/login");

    const meRes = await fetch(`${API_BASE_URL}/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!meRes.ok) redirect(302, "/login");

    const me = await meRes.json();
    const isSuperuser = me.role === "superuser";
    const isProjectManager = me.is_project_manager === true;

    if (!isSuperuser && !isProjectManager) {
        error(403, "Access required");
    }

    const headers = { Authorization: `Bearer ${token}` };

    // Project managers see only their projects; superusers see all.
    const projectsRes = await fetch(`${API_BASE_URL}/projects`, { headers });
    const projects = projectsRes.ok ? await projectsRes.json() : [];

    if (!isSuperuser) {
        return { isSuperuser, projects, allUsers: [], ontologies: [], proposedEntities: [], proposedTotal: 0 };
    }

    const [ontologiesRes, proposedRes, usersRes] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/ontologies`, { headers }),
        fetch(`${API_BASE_URL}/admin/entities/proposed?limit=50&offset=0`, { headers }),
        fetch(`${API_BASE_URL}/admin/users`, { headers }),
    ]);

    const ontologies = ontologiesRes.ok ? await ontologiesRes.json() : [];
    const proposedData = proposedRes.ok
        ? await proposedRes.json()
        : { entities: [], total: 0 };
    const allUsers = usersRes.ok ? await usersRes.json() : [];

    return {
        isSuperuser,
        projects,
        allUsers,
        ontologies,
        proposedEntities: proposedData.entities,
        proposedTotal: proposedData.total,
    };
};
