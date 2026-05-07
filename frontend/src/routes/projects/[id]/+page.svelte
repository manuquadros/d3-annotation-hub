<script lang="ts">
    import { page } from "$app/stores";
    import type { PageData } from "./$types";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();
    const projectId = $derived($page.params.id);
</script>

<div class="hub">
    <h1>{data.projectName ?? "Project Management"}</h1>

    <div class="cards">
        <a class="card" href="/projects/{projectId}/documents">
            <div class="card-icon">
                <i class="ph ph-file-text"></i>
            </div>
            <div class="card-body">
                <h2>Documents</h2>
                <p>Add or remove references from the project's annotation queue.</p>
            </div>
            <i class="ph ph-arrow-right card-arrow"></i>
        </a>

        <a class="card" href="/projects/{projectId}/ontologies">
            <div class="card-icon">
                <i class="ph ph-tree-structure"></i>
            </div>
            <div class="card-body">
                <h2>Ontologies</h2>
                <p>Import OWL ontologies or assign existing ones to this project.</p>
            </div>
            <i class="ph ph-arrow-right card-arrow"></i>
        </a>

        <a class="card" href="/projects/{projectId}/users">
            <div class="card-icon">
                <i class="ph ph-users"></i>
            </div>
            <div class="card-body">
                <h2>Users</h2>
                <p>Add annotators and curators, or remove existing project members.</p>
            </div>
            <i class="ph ph-arrow-right card-arrow"></i>
        </a>
    </div>
</div>

<style>
    .hub {
        max-width: 800px;
        margin: 3rem auto;
        padding: 0 1.5rem;
    }

    h1 {
        font-size: 1.5rem;
        margin: 0 0 2rem;
        font-weight: 600;
    }

    .cards {
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }

    .card {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 1.5rem;
        padding: 1.5rem 1.75rem;
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        text-decoration: none;
        color: inherit;
        transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
    }

    .card:hover {
        border-color: #999;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
        transform: translateY(-2px);
    }

    .card-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 3.5rem;
        height: 3.5rem;
        background: #f5f5f5;
        border-radius: 10px;
        flex-shrink: 0;
        font-size: 1.75rem;
        color: #333;
    }

    .card:hover .card-icon {
        background: #ececec;
    }

    .card-body {
        flex: 1;
        min-width: 0;
    }

    .card-body h2 {
        font-size: 1.1rem;
        font-weight: 600;
        margin: 0 0 0.3rem;
    }

    .card-body p {
        font-size: 0.9rem;
        color: #666;
        margin: 0;
        line-height: 1.4;
    }

    .card-arrow {
        font-size: 1.25rem;
        color: #aaa;
        flex-shrink: 0;
    }

    .card:hover .card-arrow {
        color: #555;
    }
</style>
