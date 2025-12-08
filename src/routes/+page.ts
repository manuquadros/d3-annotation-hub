import { redirect } from "@sveltejs/kit";
import { auth } from "$lib/auth.svelte";
import { fetchReference } from "$lib/api";
import type { AnnotationState } from "$lib/annotation.svelte";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch }) => {
    if (!auth.isAuthenticated) {
        throw redirect(302, "/login");
    }

    const documentData = await fetchReference("15117974", fetch);

    return {
        documentData,
    };
};
