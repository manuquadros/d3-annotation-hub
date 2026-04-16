import { error, redirect } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export interface ReferenceInfo {
    reference_id: number;
    pubmed_id: number | null;
    title: string;
    authors: string;
    year: number;
}

export interface EntityOut {
    entity_id: string;
    preferred_name: string;
    kind: string;
    confirmed: boolean;
}

export interface EvidencePointerItem {
    offset: number;
    length: number;
}

export interface EvidenceItem {
    reference_id: number;
    pubmed_id: number | null;
    title: string;
    body: string | null;
    subject_pointers: EvidencePointerItem[];
    object_pointers: EvidencePointerItem[];
}

export interface ClaimItem {
    subject: string;
    predicate: string;
    object: string;
    evidence: EvidenceItem[];
}

export interface ClaimsData {
    claims: ClaimItem[];
    entities: Record<string, EntityOut>;
}

export const load: PageServerLoad = async ({ cookies, url, parent }) => {
    const token = cookies.get("auth_token");
    if (!token) redirect(302, "/login");

    const { currentProjectId, isCurator, isSuperuser } = await parent();

    const projectId =
        url.searchParams.get("project") !== null
            ? Number(url.searchParams.get("project"))
            : currentProjectId;

    if (projectId === null) {
        error(400, "No project selected");
    }

    if (!isCurator && !isSuperuser) {
        error(403, "Curator access required");
    }

    const headers = { Authorization: `Bearer ${token}` };

    const [queueRes, claimsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/projects/${projectId}/curation/queue`, { headers }),
        fetch(`${API_BASE_URL}/projects/${projectId}/curation/claims`, { headers }),
    ]);

    if (queueRes.status === 403 || claimsRes.status === 403) {
        error(403, "Curator access required");
    }

    const queue: ReferenceInfo[] = queueRes.ok ? await queueRes.json() : [];
    const claims: ClaimsData = claimsRes.ok
        ? await claimsRes.json()
        : { claims: [], entities: {} };

    return { projectId, queue, claims };
};
