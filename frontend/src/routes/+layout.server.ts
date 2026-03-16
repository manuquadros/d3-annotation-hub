import { redirect } from "@sveltejs/kit";
import type { LayoutServerLoad } from "./$types";

export const load: LayoutServerLoad = ({ cookies, url }) => {
    const token = cookies.get("auth_token");
    if (!token && url.pathname !== "/login") {
        redirect(302, "/login");
    }
    if (!token) return { authenticated: false, isAdmin: false };

    const meRes = await fetch(`${API_BASE_URL}/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const me = meRes.ok ? await meRes.json() : null;
    const isAdmin = me?.role === "admin";

    return { authenticated: true, isAdmin };
};
