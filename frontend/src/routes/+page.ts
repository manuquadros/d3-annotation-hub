import { fetchReference, fetchQueue } from "$lib/api";
import { redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch, url, parent }) => {
    const { currentProjectId, isAdmin, isCurator } = await parent();

    if (currentProjectId === null) {
        if (isAdmin) {
            redirect(302, "/projects/new");
        }
        return { documentData: null };
    }

    // Curators land on the curation queue by default.
    if (isCurator && !url.searchParams.get("ref")) {
        redirect(302, `/curate?project=${currentProjectId}`);
    }

    // Project managers (non-curator admins) land on the management hub.
    if (isAdmin && !isCurator && !url.searchParams.get("ref")) {
        redirect(302, `/projects/${currentProjectId}`);
    }

    const ref = url.searchParams.get("ref");

    if (!ref) {
        const queue = await fetchQueue(currentProjectId, fetch);
        const first = queue.find((item) => !item.completed) ?? queue[0];
        if (!first) {
            return { documentData: null };
        }
        redirect(
            302,
            `/?ref=${encodeURIComponent(first.ref)}&project=${currentProjectId}`,
        );
    }

    const documentData = await fetchReference(ref, currentProjectId, fetch);
    return { documentData };
};
