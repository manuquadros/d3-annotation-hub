import { fetchReference, fetchQueue } from "$lib/api";
import { redirect } from "@sveltejs/kit";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch, url }) => {
    const ref = url.searchParams.get("ref");

    if (!ref) {
        const queue = await fetchQueue(fetch);
        if (queue.length === 0) {
            return { documentData: null };
        }
        redirect(302, `/?ref=${encodeURIComponent(queue[0])}`);
    }

    const documentData = await fetchReference(ref, fetch);
    return { documentData };
};
