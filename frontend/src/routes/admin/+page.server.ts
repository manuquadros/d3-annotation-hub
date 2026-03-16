import { error, redirect } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) redirect(302, "/login");

    const meRes = await fetch(`${API_BASE_URL}/me`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    if (!meRes.ok) redirect(302, "/login");

    const me = await meRes.json();
    if (me.role !== "admin") error(403, "Admin access required");

    const ontologiesRes = await fetch(`${API_BASE_URL}/admin/ontologies`, {
        headers: { Authorization: `Bearer ${token}` },
    });
    const ontologies = ontologiesRes.ok ? await ontologiesRes.json() : [];

    return { ontologies };
};
