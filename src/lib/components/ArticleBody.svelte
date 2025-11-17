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
