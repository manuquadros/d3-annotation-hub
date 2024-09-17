<script lang="ts">
    import { onMount, createEventDispatcher } from "svelte";

    export let body: HTMLDivElement | null;

    const dispatch = createEventDispatcher();
    let processedResources = new Set<string>();

    let selectedText = "";
    let selectedSpan: HTMLSpanElement | null = null;
    let showDropdown = false;
    let showRemoveDropdown = false;
    let dropdownPosition = { x: 0, y: 0 };

    function processTags(element: HTMLElement): void {
        const spans = element.querySelectorAll("span[typeof]");

        spans.forEach((span) => {
            const type = span.getAttribute("typeof");
            const resource = span.getAttribute("resource");
            const text = span.textContent;

            if (resource && !processedResources.has(resource)) {
                processedResources.add(resource);
                dispatch("entityFound", { type, text, resource });
            }
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
            const range = selection.getRangeAt(0);
            const span = document.createElement("span");
            span.className = "entity";
            span.setAttribute("typeof", `d3o:${option}`);
            range.surroundContents(span);
            selection.removeAllRanges();
        }
        showDropdown = false;
    }

    function handleRemoveAnnotation() {
        if (selectedSpan) {
            const parent = selectedSpan.parentNode;
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
