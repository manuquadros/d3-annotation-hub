<script lang="ts">
    import type { PageData } from "./$types";

    import "../styles.css";
    import Annotation from "$lib/components/Annotation.svelte";
    import NavCards from "$lib/components/NavCards.svelte";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();

    const CARDS = {
        annotate: {
            icon: "ph-note-pencil",
            title: "Annotation Queue",
            description:
                "Work through the document queue and annotate entities and relations.",
        },
        curate: {
            icon: "ph-check-square",
            title: "Curation Queue",
            description:
                "Review and validate annotations submitted for this project.",
        },
        manage: {
            icon: "ph-gauge",
            title: "Project Management",
            description:
                "Manage documents, ontologies, and team members for this project.",
        },
        admin: {
            icon: "ph-gear",
            title: "Administration",
            description:
                "Manage all projects, import ontologies, and configure system settings.",
        },
    } as const;

    function hrefFor(dest: "annotate" | "curate" | "manage" | "admin"): string {
        if (dest === "annotate")
            return `/?go=annotate&project=${data.currentProjectId}`;
        if (dest === "curate")
            return `/curate?project=${data.currentProjectId}`;
        if (dest === "manage") return `/projects/${data.currentProjectId}`;
        return "/admin";
    }
</script>

{#if data.mode === "hub"}
    <NavCards
        heading="Where would you like to go?"
        cards={data.destinations.map((dest) => ({
            ...CARDS[dest],
            href: hrefFor(dest),
        }))}
    />
{:else if data.documentData}
    {#key data.documentData}
        <Annotation initialState={data.documentData} />
    {/key}
{:else}
    <p>No references in the queue.</p>
{/if}
