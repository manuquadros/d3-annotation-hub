import { API_BASE_URL } from "$lib/config";
import type { RequestHandler } from "@sveltejs/kit";

export const POST: RequestHandler = async ({ request, cookies }) => {
    const formData = await request.formData();

    const response = await fetch(`${API_BASE_URL}/token`, {
        method: "POST",
        body: formData,
    });

    if (!response.ok) {
        return new Response(null, { status: 401 });
    }

    const data = await response.json();

    // Derive maxAge from the JWT exp claim so it matches the backend token lifetime.
    const [, payloadB64] = data.access_token.split(".");
    const payload = JSON.parse(
        atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/")),
    );
    const maxAge = Math.max(payload.exp - Math.floor(Date.now() / 1000), 0);

    cookies.set("auth_token", data.access_token, {
        httpOnly: true,
        sameSite: "strict",
        path: "/",
        maxAge,
    });

    return new Response(null, { status: 200 });
};
