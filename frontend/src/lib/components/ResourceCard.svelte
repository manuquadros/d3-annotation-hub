<script lang="ts">
    import { getContext, onMount } from "svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import { getLabelColor } from "$lib/utils.ts";

    interface Props {
        fragment: DocumentFragment;
        pointer_id: string;
    }
    const { fragment, pointer_id }: Props = $props();
    const annState = getContext<AnnotationState>("annotationState");

    let labelColor = $derived.by(() => {
        const pointer = annState.pointer(pointer_id);
        if (!pointer) return "transparent";
        const entity = annState.entity(pointer.entity_id);
        return getLabelColor(entity?.kind ?? "");
    });

    let mountpoint: HTMLSpanElement;

    onMount(() => {
        if (mountpoint && fragment) {
            mountpoint.append(fragment);
        }
    });
</script>

<span
    bind:this={mountpoint}
    class="annotation-highlight"
    style:border-bottom="3px solid {labelColor}"
    style:background-color="{labelColor}22"
></span>

<style>
    .annotation-highlight {
        display: inline;
        border-radius: 2px;
        padding-bottom: 1px;
    }
</style>
