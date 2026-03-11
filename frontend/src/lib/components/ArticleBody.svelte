<script lang="ts">
    import { getContext, setContext, onMount } from "svelte";
    import type { Pointer, DropdownState } from "$lib/types.ts";
    import {
        annotateHTMLString,
        AnnotationState,
    } from "$lib/annotation.svelte";
    import DOMPurify from "dompurify";
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

    /**
     * Opens the labeling dropdown at the mouse cursor position.
     *
     * @param event - The mouse event containing cursor position
     * @param container - The container element that triggered the dropdown
     * @param dropdownState - The current dropdown state to update
     * @returns The updated dropdown state
     */
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

    /**
     * Retrieves the selected range if the selection is valid and within the container.
     *
     * @param selection - The current window selection
     * @param container - The container element to check selection against
     * @returns The selected Range if valid, null otherwise
     */
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
     * Handles text selection by updating the selected range and opening the labeling dropdown.
     *
     * @param event - The mouse event from the selection
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

    /**
     * Finds plain text offsets for the search text within the original HTML body.
     * When a range is provided, returns the offset of that specific selection.
     * Otherwise, finds all occurrences of the search text.
     *
     * @param htmlBody - The original HTML body string (without annotations)
     * @param searchText - The text to search for
     * @param range - Optional range to calculate offset for (for single occurrence)
     * @param containerElement - Optional container element (required when range is provided)
     * @returns Array of plain text offsets where the search text occurs
     */
    function findTextOffsets(
        htmlBody: string,
        searchText: string,
        range?: Range,
        containerElement?: HTMLElement,
    ): number[] {
        const offsets: number[] = [];

        // Extract plain text from original HTML (without annotations)
        const tempDiv = document.createElement("div");
        tempDiv.innerHTML = DOMPurify.sanitize(htmlBody);
        const plainText = tempDiv.textContent || "";

        if (range && containerElement) {
            // Calculate offset of the specific range in the current DOM
            const walker = document.createTreeWalker(
                containerElement,
                NodeFilter.SHOW_TEXT,
                null,
            );

            let currentOffset = 0;
            let node;
            while ((node = walker.nextNode())) {
                if (node === range.startContainer) {
                    offsets.push(currentOffset + range.startOffset);
                    break;
                }
                currentOffset += (node.textContent || "").length;
            }
        } else {
            // Find all occurrences in the plain text
            let index = 0;
            while ((index = plainText.indexOf(searchText, index)) !== -1) {
                offsets.push(index);
                index += searchText.length;
            }
        }

        return offsets;
    }

    /**
     * Handles label selection from the dropdown by creating annotations.
     * If the selected text starts with a number, only the selected occurrence is annotated.
     * Otherwise, all occurrences of the text are annotated.
     *
     * @param label - The label to apply to the annotation(s)
     */
    function handleLabelSelect(label: string) {
        if (!selectedRange) return;

        const rangeText = selectedRange.toString().trim();
        const bodyElement = document.getElementById("article-body");
        if (!bodyElement) return;

        // Check if text starts with a number - if so, only annotate the selected occurrence
        const startsWithNumber = /^\d/.test(rangeText);

        const offsets = startsWithNumber
            ? findTextOffsets(body, rangeText, selectedRange, bodyElement)
            : findTextOffsets(body, rangeText);

        // Batch add all annotations to avoid DOM changes invalidating offsets
        annotationState.add(
            label,
            offsets.map((offset) => ({ offset, length: rangeText.length })),
        );

        // Clear selection
        window.getSelection()?.removeAllRanges();
        selectedRange = null;
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
