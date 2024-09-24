<script lang="ts">
    import { onMount } from "svelte";
    import { resources } from "$lib/resources.ts";
    import {
        showDropdown,
        showRemoveDropdown,
        dropdownPosition,
        handleOptionClick,
        handleSpanClick,
        handleTextSelection,
        handleRemoveAnnotation,
    } from "$lib/handlers.ts";

    export let body: HTMLDivElement | null;

    function processTags(content: HTMLDivElement): void {
        const spans = content.querySelectorAll("span[typeof]");

        spans.forEach((span) => {
            resources.storeEntitySpan(span);
        });
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
        <button class="dropdown-button" on:click={handleRemoveAnnotation}
            >Remove annotation</button
        >
    </div>
{/if}
