import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ params, parent }) => {
    const { projects } = await parent();
    const project = projects.find((p) => p.project_id === Number(params.id));
    return { projectName: project?.name ?? null };
};
