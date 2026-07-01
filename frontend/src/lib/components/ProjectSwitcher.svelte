<script lang="ts">
    import { goto } from "$app/navigation";
    import { setLastProject } from "$lib/api";

    let {
        projects,
        currentProjectId,
        isAdmin = false,
    }: {
        projects: Array<{ project_id: number; name: string }>;
        currentProjectId: number | null;
        isAdmin?: boolean;
    } = $props();

    let open = $state(false);

    const currentProject = $derived(
        projects.find((p) => p.project_id === currentProjectId) ?? projects[0],
    );

    async function switchTo(id: number) {
        open = false;
        await setLastProject(id);
        goto(`/?project=${id}`);
    }

    function toggle() {
        open = !open;
    }

    function onKeydown(e: KeyboardEvent) {
        if (e.key === "Escape") open = false;
    }
</script>

<svelte:window onkeydown={onKeydown} />

<div class="switcher" class:open>
    <button class="trigger" onclick={toggle} aria-expanded={open}>
        <span class="project-label">{currentProject?.name ?? "No project"}</span
        >
        <i class="ph ph-caret-up-down chevron"></i>
    </button>

    {#if open}
        <div
            class="backdrop"
            role="button"
            tabindex="-1"
            aria-label="Close menu"
            onclick={() => (open = false)}
            onkeydown={(e) => e.key === "Enter" && (open = false)}
        ></div>
        <div class="dropdown">
            {#each projects as p (p.project_id)}
                <button
                    class="item"
                    class:active={p.project_id === currentProjectId}
                    onclick={() => switchTo(p.project_id)}
                >
                    {p.name}
                </button>
            {/each}

            {#if isAdmin}
                <div class="divider"></div>
                <a
                    class="item new-project"
                    href="/projects/new"
                    onclick={() => (open = false)}
                >
                    <i class="ph ph-plus"></i>
                    Create new project
                </a>
            {/if}
        </div>
    {/if}
</div>

<style>
    .switcher {
        position: relative;
        margin: 0 2.5rem;
    }

    .trigger {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 0.45rem 0.6rem;
        background: var(--bg-card, #fff);
        border: 1px solid var(--border, #ddd);
        border-radius: 6px;
        cursor: pointer;
        font-size: 0.875rem;
        font-weight: 600;
        text-align: left;
        gap: 0.5rem;
        transition: border-color 0.15s;
    }

    .trigger:hover {
        border-color: var(--border-hover, #aaa);
    }

    .project-label {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .chevron {
        flex-shrink: 0;
        font-size: 0.85rem;
        color: #888;
    }

    .backdrop {
        position: fixed;
        inset: 0;
        z-index: 10;
    }

    .dropdown {
        position: absolute;
        top: calc(100% + 4px);
        left: 0;
        right: 0;
        background: #fff;
        border: 1px solid var(--border, #ddd);
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        z-index: 11;
        overflow: hidden;
        padding: 0.25rem 0;
    }

    .item {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        width: 100%;
        padding: 0.45rem 0.7rem;
        background: none;
        border: none;
        font-size: 0.875rem;
        text-align: left;
        cursor: pointer;
        color: inherit;
        text-decoration: none;
    }

    .item:hover {
        background: var(--bg-hover, #f5f5f5);
    }

    .item.active {
        font-weight: 600;
        color: var(--color-primary, #333);
    }

    .divider {
        height: 1px;
        background: var(--border, #eee);
        margin: 0.25rem 0;
    }

    .new-project {
        color: var(--color-primary, #444);
    }

    .new-project i {
        font-size: 0.8rem;
    }
</style>
