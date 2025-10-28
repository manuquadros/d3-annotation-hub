import { AnnotationStateSchema } from "$lib/types";

export async function load({
    fetch,
}): Promise<{ documentData: AnnotationState }> {
    const response = await fetch(
        `http://localhost:8000/reference/?ref_identifier=15117974
        &user=f47f7e7b-3913-457e-911c-6da6275de3ec`,
    );
    const documentResponse = await response.json();

    return {
        documentData: AnnotationStateSchema.parse(JSON.parse(documentResponse)),
    };
}
