<script lang="ts">
    import { page } from "$app/stores";
    import type { PageData } from "./$types";
    import NavCards from "$lib/components/NavCards.svelte";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();
    const projectId = $derived($page.params.id);

    const cards = $derived([
        {
            href: `/projects/${projectId}/documents`,
            icon: "ph-file-text",
            title: "Documents",
            description:
                "Add or remove references from the project's annotation queue.",
        },
        {
            href: `/projects/${projectId}/ontologies`,
            icon: "ph-tree-structure",
            title: "Ontologies",
            description:
                "Import OWL ontologies or assign existing ones to this project.",
        },
        {
            href: `/projects/${projectId}/users`,
            icon: "ph-users",
            title: "Users",
            description:
                "Add annotators and curators, or remove existing project members.",
        },
    ]);
</script>

<NavCards heading={data.projectName ?? "Project Management"} {cards} />
