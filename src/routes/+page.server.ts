import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ fetch, url }) => {
    const annotator = url.searchParams.get("annotator");
    const id = url.searchParams.get("id");

    try {
        let url: string;
        if (annotator && id) {
            url = `http://localhost:8000/annotation/?annotator=${annotator}&id=${id}`;
        } else if (id) {
            console.log(`loading article ${id}`);
            url = `http://localhost:8000/segment/?pmid=${id}`;
        } else {
            console.log("start and pmid are null");
            url = "http://localhost:8000/segment/";
        }
        const response = await fetch(url);
        const data = await response.json();

        return {
            document: JSON.parse(data).content,
        };
    } catch (err) {
        console.error(err);
    }
};
