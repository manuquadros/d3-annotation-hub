<script lang="ts">
    import type { PageData } from "./$types";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();
</script>

<div class="content-container">
    <h2>Curation Queue</h2>

    {#if data.queue.length === 0}
        <p>No references are ready for curation yet.</p>
    {:else}
        <table class="table">
            <thead>
                <tr>
                    <th>PubMed ID</th>
                    <th>Title</th>
                    <th>Authors</th>
                    <th>Year</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {#each data.queue as ref (ref.reference_id)}
                    <tr>
                        <td>{ref.pubmed_id ?? "—"}</td>
                        <td>{ref.title}</td>
                        <td>{ref.authors}</td>
                        <td>{ref.year}</td>
                        <td>
                            <a
                                class="btn btn-sm primary"
                                href="/curate/{ref.reference_id}?project={data.projectId}"
                            >
                                Review
                            </a>
                        </td>
                    </tr>
                {/each}
            </tbody>
        </table>
    {/if}
</div>
