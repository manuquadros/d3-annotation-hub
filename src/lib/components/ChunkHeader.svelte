<script lang="ts">
    interface Props {
        header?: Element | null;
    }

    let { header = null }: Props = $props();
</script>

{#if header}
    <div id="header">
        {@html header.innerHTML}
    </div>
{/if}
