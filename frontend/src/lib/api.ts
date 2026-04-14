import { goto } from "$app/navigation";
import { AnnotationState } from "$lib/annotation.svelte";
import type { EntitySearchResult } from "$lib/types.ts";

export async function fetchReference(
    refIdentifier: string,
    projectId: number,
    customFetch: typeof fetch = fetch,
): Promise<AnnotationState> {
    const params = new URLSearchParams({
        ref_identifier: refIdentifier,
        project_id: String(projectId),
    });
    const response = await customFetch(`/api/reference?${params}`);

    if (response.status === 401) {
        goto("/login");
        throw new Error("Not authenticated");
    }

    if (!response.ok) {
        throw new Error(`Failed to fetch reference: ${response.statusText}`);
    }

    const data = await response.json();
    return new AnnotationState(data);
}

export interface QueueItem {
    ref: string;
    completed: boolean;
}

export async function fetchQueue(
    projectId: number,
    customFetch: typeof fetch = fetch,
): Promise<QueueItem[]> {
    const response = await customFetch(`/api/projects/${projectId}/queue`);

    if (!response.ok) {
        throw new Error(`Failed to fetch queue: ${response.statusText}`);
    }

    return response.json();
}

export async function markQueueItemComplete(
    projectId: number,
    ref: string,
): Promise<void> {
    const response = await fetch(
        `/api/projects/${projectId}/queue?ref=${encodeURIComponent(ref)}`,
        { method: "POST" },
    );
    if (!response.ok) {
        throw new Error(`Failed to mark complete: ${response.statusText}`);
    }
}

export async function markQueueItemIncomplete(
    projectId: number,
    ref: string,
): Promise<void> {
    const response = await fetch(
        `/api/projects/${projectId}/queue?ref=${encodeURIComponent(ref)}`,
        { method: "DELETE" },
    );
    if (!response.ok) {
        throw new Error(`Failed to mark incomplete: ${response.statusText}`);
    }
}

export async function setLastProject(projectId: number): Promise<void> {
    await fetch(`/api/me/last-project?project_id=${projectId}`, {
        method: "PUT",
    });
}

export interface KindOption {
    curie: string;
    label: string;
}

export async function fetchEntityTypes(): Promise<KindOption[]> {
    const response = await fetch("/api/entity/types");
    if (!response.ok) return [];
    const items: Array<{ entity_id: string; preferred_name: string }> = await response.json();
    return items.map((item) => ({ curie: item.entity_id, label: item.preferred_name }));
}

export async function searchEntities(
    q: string,
    limit = 20,
    projectId?: number,
): Promise<EntitySearchResult[]> {
    const params = new URLSearchParams({ q, limit: String(limit) });
    if (projectId !== undefined) params.set("project_id", String(projectId));
    const response = await fetch(`/api/entity?${params}`);
    if (!response.ok) {
        throw new Error(`Entity search failed: ${response.statusText}`);
    }
    return response.json();
}

export interface PropertyOption {
    curie: string;
    label: string;
    domain_curie: string | null;
    range_curie: string | null;
}

export async function submitProposedProperty(
    projectId: number,
    proposal: { label: string; curie?: string; domain_curie?: string; range_curie?: string },
): Promise<void> {
    await fetch(`/api/projects/${projectId}/proposed-properties`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(proposal),
    });
}

export async function submitProposedEntity(
    projectId: number,
    proposal: { label: string; curie: string; kind: string },
): Promise<void> {
    await fetch(`/api/projects/${projectId}/proposed-entities`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(proposal),
    });
}

export async function fetchProjectProperties(
    projectId: number,
): Promise<PropertyOption[]> {
    const response = await fetch(`/api/projects/${projectId}/properties`);
    if (!response.ok) return [];
    return response.json();
}

export async function saveAnnotation(jsonData: string): Promise<void> {
    const response = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ json_data: jsonData }),
    });

    if (!response.ok) {
        const err = new Error(`Failed to save annotation: ${response.statusText}`) as Error & { status: number };
        err.status = response.status;
        throw err;
    }
}
