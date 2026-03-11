import { redirect } from "@sveltejs/kit";
import { auth } from "$lib/auth.svelte";
import { fetchReference } from "$lib/api";
import type { AnnotationState } from "$lib/annotation.svelte";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch, url }) => {
    if (!auth.isAuthenticated) {
        throw redirect(302, "/login");
    }

    const ref = url.searchParams.get("ref") ?? "15117974";
    const documentData = await fetchReference(ref, fetch);

    return {
        documentData,
    };
};
