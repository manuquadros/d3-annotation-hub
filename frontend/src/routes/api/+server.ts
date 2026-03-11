import type { RequestHandler } from "./$types";

export const PUT: RequestHandler = (params) => {
    console.log("test");
    console.log(params.body);

    return new Response("ok");
};
