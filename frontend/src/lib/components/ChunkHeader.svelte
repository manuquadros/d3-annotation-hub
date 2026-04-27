<script lang="ts">
    interface Props {
        header?: Element | null;
    }

    let { header = null }: Props = $props();
</script>

{#if header}
    <div id="header">
        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
        {@html header.innerHTML}
    </div>
{/if}
