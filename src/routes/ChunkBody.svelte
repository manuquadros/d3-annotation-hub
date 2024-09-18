<script lang="ts">
    import { onMount } from "svelte";
    import { removeEntity, storeEntitySpan } from "./resources.ts";
    import { rangeToClass, trimRange } from "../ranges.ts";

    export let body: HTMLDivElement | null;

    let selectedText = "";
    let selectedSpan: HTMLSpanElement | null = null;
    let showDropdown = false;
    let showRemoveDropdown = false;
    let dropdownPosition = { x: 0, y: 0 };

    function processTags(element: HTMLElement): void {
        const spans = element.querySelectorAll("span[typeof]");

        spans.forEach((span) => {
            storeEntitySpan(span);
        });
    }

    function handleTextSelection(event: MouseEvent) {
        const selection = window.getSelection();
        if (selection && !selection.isCollapsed) {
            selectedText = selection.toString().trim();
            if (selectedText) {
                showDropdown = true;
                showRemoveDropdown = false;
                dropdownPosition = { x: event.clientX, y: event.clientY };
            }
        } else {
            showDropdown = false;
        }
    }

    function handleSpanClick(event: MouseEvent) {
        const target = event.target as HTMLElement;
        if (target.classList.contains("entity")) {
            event.stopPropagation();
            selectedSpan = target as HTMLSpanElement;
            showRemoveDropdown = true;
            showDropdown = false;
            dropdownPosition = { x: event.clientX, y: event.clientY };
        } else {
            showRemoveDropdown = false;
        }
    }

    function handleOptionClick(option: string) {
        const selection = window.getSelection();
        if (selection && !selection.isCollapsed) {
            const range = trimRange(selection.getRangeAt(0));
            const span = document.createElement("span");
            const label = `d3o:${option}`;
            span.className = rangeToClass(range);
            span.setAttribute("typeof", label);
            range.surroundContents(span);
            selection.removeAllRanges();
            storeEntitySpan(span);
        }
        showDropdown = false;
    }

    function handleRemoveAnnotation() {
        if (selectedSpan) {
            const parent = selectedSpan.parentNode;
            removeEntity(
                selectedSpan.getAttribute("typeof") as string,
                selectedSpan.getAttribute("resource") as string,
            );
            if (parent) {
                while (selectedSpan.firstChild) {
                    parent.insertBefore(selectedSpan.firstChild, selectedSpan);
                }
                parent.removeChild(selectedSpan);
            }
        }
        showRemoveDropdown = false;
    }

    onMount(() => {
        if (body) {
            processTags(body);
        }
    });
</script>

<div on:click={handleSpanClick} on:mouseup={handleTextSelection}>
    {#if body}
        {@html body.innerHTML}
    {/if}
</div>

{#if showDropdown}
    <div
        class="dropdown"
        style="position: absolute; left: {dropdownPosition.x}px; top: {dropdownPosition.y}px;"
    >
        <button on:click={() => handleOptionClick("Enzyme")}>Enzyme</button>
        <button on:click={() => handleOptionClick("Bacteria")}>Bacteria</button>
        <button on:click={() => handleOptionClick("Strain")}>Strain</button>
    </div>
{/if}

{#if showRemoveDropdown}
    <div
        class="dropdown"
        style="position: absolute; left: {dropdownPosition.x}px; top: {dropdownPosition.y}px;"
    >
        <button on:click={handleRemoveAnnotation}>Remove annotation</button>
    </div>
{/if}
