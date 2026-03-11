import { goto } from "$app/navigation";
import { AnnotationState } from "$lib/annotation.svelte";

export async function fetchReference(
    refIdentifier: string,
    customFetch: typeof fetch = fetch,
): Promise<AnnotationState> {
    const url = `/api/reference?ref_identifier=${encodeURIComponent(refIdentifier)}`;
    const response = await customFetch(url);

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

export async function fetchQueue(
    customFetch: typeof fetch = fetch,
): Promise<string[]> {
    const response = await customFetch("/api/queue");

    if (!response.ok) {
        throw new Error(`Failed to fetch queue: ${response.statusText}`);
    }

    return response.json();
}

export async function saveAnnotation(jsonData: string): Promise<void> {
    const response = await fetch("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ json_data: jsonData }),
    });

    if (!response.ok) {
        throw new Error(`Failed to save annotation: ${response.statusText}`);
    }
}
