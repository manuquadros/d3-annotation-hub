<script lang="ts">
    import { getContext } from "svelte";
    import {
        annotateHTMLString,
        AnnotationState,
        extractSentence,
    } from "$lib/annotation.svelte";
    import DOMPurify from "dompurify";
    import type { EditorState } from "$lib/types.ts";
    import type { Attachment } from "svelte/attachments";

    let { body } = $props();
    const annotationState = getContext<AnnotationState>("annotationState");
    const editorStateCtx = getContext<{ value: EditorState }>("editorState");

    let container: HTMLDivElement;

    const renderAnnotated: Attachment<HTMLDivElement> = (element) => {
        annotateHTMLString(element, body, annotationState);
    };

    /**
     * Computes the plain-text offset of range.startContainer within the container,
     * using the same text-node walk as createRangeFromOffsets.
     */
    function rangeToOffset(range: Range, containerElement: HTMLElement): number {
        const walker = containerElement.ownerDocument.createTreeWalker(
            containerElement,
            NodeFilter.SHOW_TEXT,
        );
        let offset = 0;
        let node: Node | null;
        while ((node = walker.nextNode())) {
            if (node === range.startContainer) {
                return offset + range.startOffset;
            }
            offset += (node.textContent || "").length;
        }
        return offset;
    }

    function handleTextSelection(event: MouseEvent): void {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) return;

        const anchorNode = selection.anchorNode;
        if (!anchorNode || !container?.contains(anchorNode.parentNode)) return;

        const selectedText = selection.toString().trim();
        if (!selectedText) return;

        const range = selection.getRangeAt(0);
        const offset = rangeToOffset(range, container);
        const length = selectedText.length;

        // Extract plain text from the original HTML for sentence extraction
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = DOMPurify.sanitize(body);
        const plainText = tempDiv.textContent || "";

        const { start: sentenceStart } = extractSentence(plainText, offset);

        editorStateCtx.value = { mode: 'create', offset, length, sentenceStart };
        window.getSelection()?.removeAllRanges();
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    id="article-body"
    class="chunk-body"
    onmouseup={handleTextSelection}
    bind:this={container}
    {@attach renderAnnotated}
></div>
