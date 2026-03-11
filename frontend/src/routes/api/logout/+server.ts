import type { RequestHandler } from "@sveltejs/kit";

export const POST: RequestHandler = async ({ cookies }) => {
    cookies.delete("auth_token", { path: "/" });
    return new Response(null, { status: 200 });
};
