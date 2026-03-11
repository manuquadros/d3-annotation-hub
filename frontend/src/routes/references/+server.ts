import { json } from "@sveltejs/kit";

export async function GET({ params, url }) {
    const identifier = url.searchParams.get("identifier");
    const response = await fetch(
        `http://localhost:8000/reference/${identifier}`,
    );
    return response;
}
