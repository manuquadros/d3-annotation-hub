import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const GET: RequestHandler = async ({ params, url, cookies }) => {
    const token = cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    const limit = url.searchParams.get("limit") ?? "50";
    const offset = url.searchParams.get("offset") ?? "0";
    const subjectFilter = url.searchParams.get("subject_filter") ?? "";
    const predicateFilter = url.searchParams.get("predicate_filter") ?? "";
    const objectFilter = url.searchParams.get("object_filter") ?? "";
    const qs = new URLSearchParams({ limit, offset, subject_filter: subjectFilter, predicate_filter: predicateFilter, object_filter: objectFilter });
    return fetch(
        `${API_BASE_URL}/admin/ontologies/${params.id}/triples?${qs}`,
        { headers: { Authorization: `Bearer ${token}` } },
    );
};
