import { error } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";
import type { PageServerLoad } from "./$types";

export const load: PageServerLoad = async ({ cookies, params, parent }) => {
    const { isAdmin } = await parent();
    if (!isAdmin) error(403, "Access required");

    const token = cookies.get("auth_token")!;
    const headers = { Authorization: `Bearer ${token}` };
    const ontologyId = params.ontologyId;
    const projectId = params.id;

    const [ontologiesRes, entitiesRes, triplesRes, propertiesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/projects/${projectId}/ontologies`, { headers }),
        fetch(`${API_BASE_URL}/admin/ontologies/${ontologyId}/entities?limit=50&offset=0`, { headers }),
        fetch(`${API_BASE_URL}/admin/ontologies/${ontologyId}/triples?limit=50&offset=0`, { headers }),
        fetch(`${API_BASE_URL}/admin/ontologies/${ontologyId}/properties`, { headers }),
    ]);

    const allProjectOntologies = ontologiesRes.ok ? await ontologiesRes.json() : [];
    const ontology = allProjectOntologies.find(
        (o: { ontology_id: number }) => String(o.ontology_id) === ontologyId,
    );
    if (!ontology) error(404, "Ontology not found in this project");

    const entitiesData = entitiesRes.ok ? await entitiesRes.json() : { entities: [], total: 0 };
    const triplesData = triplesRes.ok ? await triplesRes.json() : { triples: [], total: 0 };
    const properties = propertiesRes.ok ? await propertiesRes.json() : [];

    return {
        ontology,
        entities: entitiesData.entities ?? [],
        entitiesTotal: entitiesData.total ?? 0,
        triples: triplesData.triples ?? [],
        triplesTotal: triplesData.total ?? 0,
        properties,
        projectId,
    };
};
