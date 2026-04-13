<script lang="ts">
    import { goto } from "$app/navigation";
    import { setLastProject } from "$lib/api";

    let {
        projects,
        currentProjectId,
    }: {
        projects: Array<{ project_id: number; name: string }>;
        currentProjectId: number | null;
    } = $props();

    async function onchange(e: Event) {
        const id = Number((e.target as HTMLSelectElement).value);
        await setLastProject(id);
        goto(`/?project=${id}`);
    }
</script>

{#if projects.length > 1}
    <select value={currentProjectId} {onchange}>
        {#each projects as p}
            <option value={p.project_id}>{p.name}</option>
        {/each}
    </select>
{:else if projects.length === 1}
    <span class="project-name">{projects[0].name}</span>
{/if}

<style>
    select {
        width: 100%;
        padding: 0.375rem 0.5rem;
        border-radius: 4px;
        border: 1px solid var(--border, #ccc);
        background: var(--bg-select, #fff);
        font-size: 0.875rem;
        cursor: pointer;
    }

    .project-name {
        display: block;
        padding: 0.375rem 0.5rem;
        font-size: 0.875rem;
        font-weight: 600;
    }
</style>
