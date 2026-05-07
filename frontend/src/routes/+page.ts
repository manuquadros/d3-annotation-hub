import { fetchReference, fetchQueue } from "$lib/api";
import { redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

type Destination = "annotate" | "curate" | "manage" | "admin";

export const load: PageLoad = async ({ fetch, url, parent }) => {
    const { currentProjectId, isAdmin, isSuperuser, isCurator, isAnnotator, isProjectManager } =
        await parent();

    const canManageProjects = isAdmin && !isSuperuser;

    if (currentProjectId === null) {
        if (isSuperuser) redirect(302, "/admin");
        if (canManageProjects) redirect(302, "/projects/new");
        return { documentData: null };
    }

    const destinations: Destination[] = [];
    if (isAnnotator) destinations.push("annotate");
    if (isCurator) destinations.push("curate");
    if (isProjectManager) destinations.push("manage");
    if (isSuperuser) destinations.push("admin");

    if (isProjectManager && destinations.length === 0) {
        redirect(302, `/projects/${currentProjectId}`);
    }

    const go = url.searchParams.get("go") as Destination | null;
    const ref = url.searchParams.get("ref");

    if (destinations.length > 1 && !go && !ref) {
        return { mode: "hub" as const, destinations, documentData: null };
    }

    const destination = go ?? destinations[0];

    if (!ref) {
        if (destination === "admin") redirect(302, "/admin");
        if (destination === "manage") redirect(302, `/projects/${currentProjectId}`);
        if (destination === "curate") redirect(302, `/curate?project=${currentProjectId}`);
        const queue = await fetchQueue(currentProjectId, fetch);
        const first = queue.find((item) => !item.completed) ?? queue[0];
        if (!first) return { documentData: null };
        redirect(302, `/?ref=${encodeURIComponent(first.ref)}&project=${currentProjectId}`);
    }

    const documentData = await fetchReference(ref, currentProjectId, fetch);
    return { documentData };
};
