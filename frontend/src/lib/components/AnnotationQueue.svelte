<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { fetchQueue } from "$lib/api";

    let queue = $state<string[]>([]);
    let error = $state<string | null>(null);
    let loading = $state(true);

    let currentRef = $derived($page.url.searchParams.get("ref"));

    onMount(async () => {
        try {
            queue = await fetchQueue();
        } catch (e) {
            error = e instanceof Error ? e.message : "Failed to load queue";
        } finally {
            loading = false;
        }
    });
</script>

{#if loading}
    <span class="queue-status">Loading...</span>
{:else if error}
    <span class="queue-status queue-error">{error}</span>
{:else if queue.length === 0}
    <span class="queue-status">Queue is empty</span>
{:else}
    {#each queue as identifier}
        <a
            href="/?ref={identifier}"
            class:active={currentRef === identifier}
            onclick={(e) => {
                e.preventDefault();
                goto(`/?ref=${identifier}`);
            }}
        >
            {identifier}
        </a>
    {/each}
{/if}

<style>
    .sidebar-label {
        display: block;
        padding: 0.5rem 1rem;
        font-weight: bold;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.6;
    }

    .queue-status {
        display: block;
        padding: 0.25rem 1rem;
        font-size: 0.875rem;
        opacity: 0.7;
    }

    .queue-error {
        color: red;
    }
</style>
