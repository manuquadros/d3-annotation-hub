import type { RequestHandler } from "./$types";

export const PUT: RequestHandler = (_params) => {
    return new Response("ok");
};
