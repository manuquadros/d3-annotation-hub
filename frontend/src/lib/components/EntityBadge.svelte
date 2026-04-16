<script lang="ts">
    import { getLabelColor, getContrastColor } from "$lib/utils.ts";

    interface Props {
        preferredName: string;
        kind: string;
    }

    let { preferredName, kind }: Props = $props();

    const labelColor = $derived(getLabelColor(kind));
    const textColor = $derived(getContrastColor(labelColor));
</script>

<span
    class="entity-badge"
    style:background-color={labelColor}
    style:color={textColor}
>
    {preferredName}
</span>

<style>
    .entity-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 0.65rem;
        border-radius: 4px;
        font-size: 1.4rem;
        font-weight: 500;
    }
</style>
