import { fetchReference, fetchQueue } from "$lib/api";
import { redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch, url, parent }) => {
    const { currentProjectId } = await parent();

    if (currentProjectId === null) {
        return { documentData: null };
    }

    const ref = url.searchParams.get("ref");

    if (!ref) {
        const queue = await fetchQueue(currentProjectId, fetch);
        if (queue.length === 0) {
            return { documentData: null };
        }
        redirect(302, `/?ref=${encodeURIComponent(queue[0])}&project=${currentProjectId}`);
    }

    const documentData = await fetchReference(ref, currentProjectId, fetch);
    return { documentData };
};
