import { error, redirect } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export interface ReferenceInfo {
    reference_id: number;
    pubmed_id: number | null;
    title: string;
    authors: string;
    year: number;
}

export const load: PageServerLoad = async ({ cookies, url, parent }) => {
    const token = cookies.get("auth_token");
    if (!token) redirect(302, "/login");

    const { currentProjectId, isCurator, isSuperuser } = await parent();

    const projectId =
        url.searchParams.get("project") !== null
            ? Number(url.searchParams.get("project"))
            : currentProjectId;

    if (projectId === null) {
        error(400, "No project selected");
    }

    if (!isCurator && !isSuperuser) {
        error(403, "Curator access required");
    }

    const res = await fetch(
        `${API_BASE_URL}/projects/${projectId}/curation/queue`,
        { headers: { Authorization: `Bearer ${token}` } },
    );

    if (res.status === 403) {
        error(403, "Curator access required");
    }

    const queue: ReferenceInfo[] = res.ok ? await res.json() : [];

    return { projectId, queue };
};
