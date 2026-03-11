import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = ({ cookies, url }) => {
    const token = cookies.get("auth_token");
    if (!token && url.pathname !== "/login") {
        redirect(302, "/login");
    }
    return { authenticated: !!token };
};
