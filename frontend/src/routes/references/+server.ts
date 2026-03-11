import { json } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";

export async function GET({ params, url }) {
    const identifier = url.searchParams.get("identifier");
    const response = await fetch(
        `${API_BASE_URL}/reference/${identifier}`,
    );
    return response;
}
