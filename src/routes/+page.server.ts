import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = () => {
    return {
        user: "teste",
    };
};
