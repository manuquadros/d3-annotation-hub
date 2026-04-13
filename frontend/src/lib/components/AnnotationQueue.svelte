<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import { page } from "$app/stores";
    import { fetchQueue, markQueueItemComplete, markQueueItemIncomplete } from "$lib/api";
    import type { QueueItem } from "$lib/api";

    let { projectId }: { projectId: number } = $props();

    let queue = $state<QueueItem[]>([]);
    let error = $state<string | null>(null);
    let loading = $state(true);

    let currentRef = $derived($page.url.searchParams.get("ref"));

    let incomplete = $derived(queue.filter((item) => !item.completed));
    let completed = $derived(queue.filter((item) => item.completed));

    onMount(async () => {
        try {
            queue = await fetchQueue(projectId);
        } catch (e) {
            error = e instanceof Error ? e.message : "Failed to load queue";
        } finally {
            loading = false;
        }
    });

    async function toggleComplete(item: QueueItem) {
        const wasCompleted = item.completed;
        queue = queue.map((q) =>
            q.ref === item.ref ? { ...q, completed: !wasCompleted } : q,
        );
        try {
            if (wasCompleted) {
                await markQueueItemIncomplete(projectId, item.ref);
            } else {
                await markQueueItemComplete(projectId, item.ref);
            }
        } catch {
            queue = queue.map((q) =>
                q.ref === item.ref ? { ...q, completed: wasCompleted } : q,
            );
        }
    }
</script>

{#if loading}
    <span class="queue-status">Loading...</span>
{:else if error}
    <span class="queue-status queue-error">{error}</span>
{:else if queue.length === 0}
    <span class="queue-status">Queue is empty</span>
{:else}
    {#each incomplete as item (item.ref)}
        <div class="queue-row">
            <a
                href="/?ref={item.ref}&project={projectId}"
                class:active={currentRef === item.ref}
                onclick={(e) => {
                    e.preventDefault();
                    goto(`/?ref=${item.ref}&project=${projectId}`);
                }}
            >
                {item.ref}
            </a>
            <button
                class="check-btn"
                title="Mark as complete"
                onclick={() => toggleComplete(item)}
            >
                <i class="ph ph-check"></i>
            </button>
        </div>
    {/each}

    {#if completed.length > 0}
        <p class="title completed-label">Completed</p>
        {#each completed as item (item.ref)}
            <div class="queue-row">
                <a
                    href="/?ref={item.ref}&project={projectId}"
                    class:active={currentRef === item.ref}
                    class="done"
                    onclick={(e) => {
                        e.preventDefault();
                        goto(`/?ref=${item.ref}&project=${projectId}`);
                    }}
                >
                    {item.ref}
                </a>
                <button
                    class="check-btn checked"
                    title="Mark as incomplete"
                    onclick={() => toggleComplete(item)}
                >
                    <i class="ph ph-check"></i>
                </button>
            </div>
        {/each}
    {/if}
{/if}

<style>
    .queue-status {
        display: block;
        padding: 0.25rem 1rem;
        font-size: 0.875rem;
        opacity: 0.7;
    }

    .queue-error {
        color: red;
    }

    /* Wrap each item to allow absolute-positioned check button */
    .queue-row {
        position: relative;
    }

    /* Replicate .sidebar-menu nav > a styles since the <a> is no longer a
       direct child of nav (the .queue-row wrapper breaks that selector). */
    .queue-row a {
        display: block;
        padding: 0.5rem 2.5rem;
        min-height: 3rem;
        height: auto;
        color: rgba(70, 70, 70, 0.8);
        background-color: transparent;
        border: 0 solid transparent;
        border-left: 0px solid transparent;
        text-decoration: none;
        /* Prevent text from running under the check button */
        padding-right: 2.5rem;
    }

    .queue-row a:hover {
        color: #464646;
        text-decoration: none;
    }

    .queue-row a.active {
        border-left-width: 8px;
        padding-left: calc(2.5rem - 8px);
        border-color: var(--primary-color);
        font-weight: 500;
    }

    .queue-row a.done {
        opacity: 0.5;
    }

    /* Section label for completed items — matches digidive p.title size/style */
    .completed-label {
        margin-top: 0.5rem;
        font-size: 0.75rem;
    }

    /* Check button: absolutely positioned on the right of the row, hidden until hover */
    .check-btn {
        position: absolute;
        right: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        cursor: pointer;
        padding: 0.2rem 0.3rem;
        border-radius: 3px;
        color: inherit;
        opacity: 0;
        font-size: 0.9rem;
        line-height: 1;
        transition: opacity 0.15s, background-color 0.15s;
    }

    .queue-row:hover .check-btn,
    .check-btn.checked {
        opacity: 1;
    }

    .check-btn.checked {
        color: var(--success-color, #2e7d32);
    }

    .check-btn:hover {
        background-color: rgba(0, 0, 0, 0.08);
    }
</style>
