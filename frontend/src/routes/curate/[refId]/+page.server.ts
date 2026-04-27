import { error, redirect } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export interface EntityOut {
    entity_id: string;
    preferred_name: string;
    kind: string;
    confirmed: boolean;
}

export interface PointerOut {
    reference_id: number;
    entity_id: string;
    offset: number;
    length: number;
}

export interface RelationOut {
    relation_id: number | null;
    predicate: string;
    subject: string;
    object: string;
}

export interface AnnotatorSnapshot {
    user_id: string;
    email: string;
    reference_id: number;
    pointers: PointerOut[];
    relations: RelationOut[];
    created_at: string;
}

export interface ReferenceInfo {
    reference_id: number;
    pubmed_id: number | null;
    title: string;
    authors: string;
    year: number;
    body: string | null;
}

export interface SnapshotsData {
    reference: ReferenceInfo;
    entities: Record<string, EntityOut>;
    snapshots: AnnotatorSnapshot[];
    curated_pointers: PointerOut[];
    curated_relations: RelationOut[];
}

export const load: PageServerLoad = async ({
    cookies,
    params,
    url,
    parent,
}) => {
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

    const referenceId = Number(params.refId);
    const res = await fetch(
        `${API_BASE_URL}/projects/${projectId}/curation/${referenceId}/snapshots`,
        { headers: { Authorization: `Bearer ${token}` } },
    );

    if (res.status === 403) error(403, "Curator access required");
    if (res.status === 404) error(404, "Reference not found");
    if (!res.ok) error(500, "Failed to load snapshots");

    const data: SnapshotsData = await res.json();

    return { projectId, referenceId, data };
};
