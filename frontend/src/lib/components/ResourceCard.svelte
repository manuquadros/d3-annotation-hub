<script lang="ts">
    import { getContext, onMount } from "svelte";
    import { AnnotationState, extractSentence } from "$lib/annotation.svelte";
    import { getLabelColor } from "$lib/utils.ts";
    import type { EditorState } from "$lib/types.ts";
    import DOMPurify from "dompurify";

    interface Props {
        fragment: DocumentFragment;
        pointer_id: string;
    }
    const { fragment, pointer_id }: Props = $props();
    const annState = getContext<AnnotationState>("annotationState");
    const editorStateCtx = getContext<{ value: EditorState }>("editorState");

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

    function handleClick() {
        const pointer = annState.pointer(pointer_id);
        if (!pointer) return;

        const body = annState.reference.body;
        if (!body) return;

        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = DOMPurify.sanitize(body);
        const plainText = tempDiv.textContent || "";

        const { start: sentenceStart } = extractSentence(plainText, pointer.offset);

        editorStateCtx.value = { mode: 'edit-pointer', pointerId: pointer_id, sentenceStart };
    }
</script>

<span
    bind:this={mountpoint}
    class="annotation-highlight"
    style:border-bottom="3px solid {labelColor}"
    style:background-color="{labelColor}22"
    role="button"
    tabindex="0"
    onclick={handleClick}
    onkeydown={(e) => e.key === 'Enter' && handleClick()}
></span>

<style>
    .annotation-highlight {
        display: inline;
        border-radius: 2px;
        padding-bottom: 1px;
        cursor: pointer;
    }
</style>
