import { redirect } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = async ({ cookies, url }) => {
    const token = cookies.get("auth_token");

    if (!token && url.pathname !== "/login") {
        redirect(302, "/login");
    }

    if (!token)
        return {
            authenticated: false,
            isSuperuser: false,
            isAdmin: false,
            isCurator: false,
            isAnnotator: false,
            isProjectManager: false,
            projects: [],
            currentProjectId: null,
        };

    const headers = { Authorization: `Bearer ${token}` };

    const [meRes, projectsRes, lastProjectRes] = await Promise.all([
        fetch(`${API_BASE_URL}/me`, { headers }),
        fetch(`${API_BASE_URL}/projects`, { headers }),
        fetch(`${API_BASE_URL}/me/last-project`, { headers }),
    ]);

    if (meRes.status === 401) {
        cookies.delete("auth_token", { path: "/" });
        redirect(302, "/login");
    }

    const me = meRes.ok ? await meRes.json() : null;
    const projects: Array<{ project_id: number; name: string }> = projectsRes.ok
        ? await projectsRes.json()
        : [];
    const lastProject = lastProjectRes.ok ? await lastProjectRes.json() : null;

    // Determine the active project ID. Priority order:
    //   1. ?project=X query param (explicit override, e.g. curation queue)
    //   2. Project ID embedded in the URL path: /projects/{id}/...
    //   3. Stored last-project for this user
    //   4. First project in the user's project list
    const urlProject = url.searchParams.get("project");
    const pathMatch = url.pathname.match(/^\/projects\/(\d+)/);
    const pathProjectId = pathMatch ? Number(pathMatch[1]) : null;
    const currentProjectId: number | null =
        urlProject !== null
            ? Number(urlProject)
            : (pathProjectId ??
              lastProject?.project_id ??
              projects[0]?.project_id ??
              null);

    const isSuperuser = me?.is_super_user === true;
    const isAdmin = me?.can_manage === true || isSuperuser;

    let isCurator = false;
    let isAnnotator = false;
    let isProjectManager = false;
    if (currentProjectId !== null) {
        const rolesRes = await fetch(
            `${API_BASE_URL}/me/project-roles?project_id=${currentProjectId}`,
            { headers },
        );
        if (rolesRes.ok) {
            const roles = (await rolesRes.json()).roles as string[];
            isCurator = roles.includes("curator");
            isAnnotator = roles.includes("annotator");
            isProjectManager = roles.includes("manager");
        }
    }

    return {
        authenticated: true,
        isSuperuser,
        isAdmin,
        isCurator,
        isAnnotator,
        isProjectManager,
        projects,
        currentProjectId,
    };
};
