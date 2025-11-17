<script lang="ts">
    import { getContext, setContext, onMount } from "svelte";
    import type { Pointer, DropdownState } from "$lib/types.ts";
    import {
        annotateHTMLString,
        AnnotationState,
    } from "$lib/annotation.svelte";
    import LabelDropdown from "./LabelDropdown.svelte";
    import type { Attachment } from "svelte/attachments";

    let { body } = $props();
    const annotationState = getContext<AnnotationState>("annotationState");
    let dropdownState = getContext<{
        isOpen: boolean;
        position: { top: number; left: number };
        triggerElement: HTMLElement | null;
    }>("dropdownState");

    let container: HTMLDivElement;
    let selectedRange: Range | null = null;

    const renderAnnotated: Attachment = (element: HTMLDivElement) => {
        // Access the derived value to make this reactive
        annotateHTMLString(element, body, annotationState);
    };

    function openLabelingDropdown(
        event: MouseEvent,
        container: HTMLElement,
        dropdownState: DropdownState,
    ): DropdownState {
        // Position dropdown at mouse location
        dropdownState.position = {
            top: event.clientY + window.scrollY,
            left: event.clientX + window.scrollX,
        };
        dropdownState.triggerElement = container;
        dropdownState.isOpen = true;
        return dropdownState;
    }

    function getSelectedRange(
        selection: Selection,
        container: HTMLElement,
    ): Range | null {
        if (selection && selection.anchorNode && !selection.isCollapsed) {
            if (
                container &&
                container.contains(selection.anchorNode.parentNode)
            ) {
                const selectedText = selection.toString().trim();
                if (selectedText) {
                    return selection.getRangeAt(0);
                }
            }
        }
        return null;
    }

    /**
     * Update selectedRange and open the text labeling dropdown.
     *
     * @param event - MouseEvent object
     */
    function handleTextSelection(event: MouseEvent): void {
        const selection: Selection | null = window.getSelection();
        if (selection && !selection.isCollapsed) {
            selectedRange = getSelectedRange(selection, container);
            dropdownState = openLabelingDropdown(
                event,
                container,
                dropdownState,
            );
        }
    }

    function handleLabelSelect(label: string) {
        if (!selectedRange) return;

        const rangeText = selectedRange.toString().trim();

        // Check if text starts with a number - if so, only annotate the selected occurrence
        const startsWithNumber = /^\d/.test(rangeText);

        if (startsWithNumber) {
            // Find the offset of the currently selected text
            // We approximate by getting text before the selection
            const selectionStart = selectedRange.startContainer;
            const selectionOffset = selectedRange.startOffset;

            // Get all text nodes before this one to calculate offset
            const bodyElement = document.getElementById("article-body");
            if (bodyElement) {
                const textNodes: Text[] = [];
                const walker = document.createTreeWalker(
                    bodyElement,
                    NodeFilter.SHOW_TEXT,
                    null,
                );

                let offset = 0;
                let node;
                while ((node = walker.nextNode())) {
                    if (node === selectionStart) {
                        offset += selectionOffset;
                        break;
                    }
                    offset += (node.textContent || "").length;
                }
                annotationState.add(label, offset, rangeText.length);
            }
        } else {
            // For strings, find and annotate all occurrences
            const searchText = rangeText;

            // Create a temporary div to get plain text from HTML
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = body;
            const plainText = tempDiv.textContent || "";

            let startIndex = 0;
            let foundIndex: number;

            while (
                (foundIndex = plainText.indexOf(searchText, startIndex)) !== -1
            ) {
                annotationState.add(label, foundIndex, searchText.length);
                startIndex = foundIndex + searchText.length;
            }
        }

        // Clear selection
        window.getSelection()?.removeAllRanges();
        selectedRange = null;

        // Re-render happens automatically via annotationData derived value
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

{#if dropdownState.isOpen && dropdownState.triggerElement === container}
    <LabelDropdown onSelect={handleLabelSelect} />
{/if}
