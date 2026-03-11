import { goto } from "$app/navigation";
import { auth } from "$lib/auth.svelte";
import { AnnotationState } from "$lib/annotation.svelte";
import { API_BASE_URL } from "$lib/config";

async function authenticatedFetch(
    url: string,
    options: RequestInit = {},
    customFetch: typeof fetch = fetch,
): Promise<Response> {
    const token = auth.getToken();

    if (!token) {
        goto("/login");
        throw new Error("Not authenticated");
    }

    const headers = new Headers(options.headers);
    headers.set("Authorization", `Bearer ${token}`);

    const response = await customFetch(url, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        auth.logout();
        throw new Error("Unauthorized");
    }

    return response;
}

export async function fetchReference(
    refIdentifier: string,
    customFetch?: typeof fetch,
): Promise<AnnotationState> {
    const url = `${API_BASE_URL}/reference/?ref_identifier=${encodeURIComponent(refIdentifier)}`;
    const response = await authenticatedFetch(url, {}, customFetch);

    if (!response.ok) {
        throw new Error(`Failed to fetch reference: ${response.statusText}`);
    }

    const data = await response.json();
    return new AnnotationState(data);
}

export async function fetchQueue(customFetch?: typeof fetch): Promise<string[]> {
    const url = `${API_BASE_URL}/queue/`;
    const response = await authenticatedFetch(url, {}, customFetch);

    if (!response.ok) {
        throw new Error(`Failed to fetch queue: ${response.statusText}`);
    }

    return response.json();
}

export async function saveAnnotation(jsonData: string): Promise<void> {
    const url = `${API_BASE_URL}/save/`;
    const response = await authenticatedFetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ json_data: jsonData }),
    });

    if (!response.ok) {
        throw new Error(`Failed to save annotation: ${response.statusText}`);
    }
}
