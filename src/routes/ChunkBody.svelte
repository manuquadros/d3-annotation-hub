<script lang="ts">
    import { onMount } from "svelte";
    import { resources } from "$lib/resources.ts";
    import {
        handleOptionClick,
        handleSpanClick,
        handleTextSelection,
        handleRemoveAnnotation,
    } from "$lib/handlers.ts";
    import { optionsDropdown, removeDropdown } from "$lib/dropdown.ts";

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

<div class="chunk-body" on:mouseup={handleTextSelection}>
    {#if body}
        {@html body.innerHTML}
    {/if}
</div>

{#if $optionsDropdown.visible}
    <div
        class="dropdown"
        style="position: absolute;
               left: {$optionsDropdown.x}px;
               top: {$optionsDropdown.y}px;"
    >
        <button on:click={() => handleOptionClick("Enzyme")}>Enzyme</button>
        <button on:click={() => handleOptionClick("Bacteria")}>Bacteria</button>
        <button on:click={() => handleOptionClick("Strain")}>Strain</button>
    </div>
{/if}

{#if $removeDropdown.visible}
    <div
        class="dropdown"
        style="position: absolute;
               left: {$removeDropdown.x}px;
               top: {$removeDropdown.y}px;"
    >
        <button class="dropdown-button" on:click={handleRemoveAnnotation}
            >Remove annotation</button
        >
    </div>
{/if}
