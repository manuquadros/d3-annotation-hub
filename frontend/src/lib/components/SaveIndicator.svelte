<script lang="ts">
    export type SaveStatus =
        | { type: 'idle' }
        | { type: 'saving' }
        | { type: 'saved', timestamp: Date }
        | { type: 'error', message: string };

    interface Props {
        status: SaveStatus;
        onRetry?: () => void;
    }

    let { status, onRetry }: Props = $props();

    function formatTime(date: Date): string {
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    }
</script>

<div class="save-indicator">
    {#if status.type === 'saving'}
        <span class="status saving">Saving…</span>
    {:else if status.type === 'saved'}
        <span class="status saved">Saved at {formatTime(status.timestamp)}</span>
    {:else if status.type === 'error'}
        <button class="status error" onclick={onRetry}>
            Error – click to retry
        </button>
    {/if}
</div>

<style>
    .save-indicator {
        position: fixed;
        bottom: 1rem;
        right: 1rem;
        z-index: 1000;
    }

    .status {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: 500;
        background-color: white;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        border: 1px solid #e5e7eb;
    }

    .saving {
        color: #3b82f6;
        border-color: #3b82f6;
    }

    .saved {
        color: #10b981;
        border-color: #10b981;
    }

    .error {
        color: #ef4444;
        border-color: #ef4444;
        cursor: pointer;
        background-color: white;
        transition: background-color 0.2s;
    }

    .error:hover {
        background-color: #fef2f2;
    }
</style>
