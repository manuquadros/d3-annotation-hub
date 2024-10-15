<script lang="ts">
    import { onMount } from "svelte";
    import {
        handleOptionClick,
        handleSpanClick,
        handleTextSelection,
        handleKeyPress,
        handleRemoveAnnotation,
    } from "$lib/handlers.ts";
    import { optionsDropdown, removeDropdown } from "$lib/dropdown.ts";
    import { body } from "$lib/body.ts";

    onMount(() => {
        body.initialize();
    });
</script>

<div class="chunk-body" on:mouseup={handleTextSelection}>
    {#if $body}
        {@html $body.innerHTML}
    {/if}
</div>

<svelte:window on:keyup|preventDefault={handleKeyPress} />

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
