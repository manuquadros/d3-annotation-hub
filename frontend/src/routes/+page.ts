import { fetchReference } from "$lib/api";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch, url }) => {
    const ref = url.searchParams.get("ref") ?? "15117974";
    const documentData = await fetchReference(ref, fetch);

    return {
        documentData,
    };
};
