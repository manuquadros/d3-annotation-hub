import { error } from "@sveltejs/kit";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ parent }) => {
    const { isAdmin } = await parent();
    if (!isAdmin) {
        error(403, "Admin access required");
    }
};
