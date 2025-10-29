<script lang="ts">
    import { getContext, mount, onMount } from "svelte";
    import {
        handleOptionClick,
        handleTextSelection,
        handleRemove,
        handleKeyPress,
    } from "$lib/handlers.ts";
    import { optionsDropdown, removeDropdown } from "$lib/dropdown.ts";
    import type { BodyStore } from "$lib/body.svelte.ts";
    import ChunkButton from "$lib/components/ChunkButton.svelte";
    import { isValidEntitySpan } from "$lib/utils";
    import { annotateHTMLString } from "$lib/annotation.ts";

    let { body } = $props();
    const entities = getContext("entities");
    const pointers = getContext("pointers");

    let container: HTMLDivElement;

    const renderAnnotated: Attachment = (element: HTMLDivElement) => {
        annotateHTMLString(element, body, entities, pointers);
    };
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    id="article-body"
    class="chunk-body"
    onmouseup={handleTextSelection}
    bind:this={container}
    {@attach renderAnnotated}
></div>

<!-- <svelte:window onkeyup={handleKeyPress} /> -->

<!-- {#if $optionsDropdown.visible} -->
<!--     <div -->
<!--         class="dropdown" -->
<!--         style="position: absolute; -->
<!--                left: {$optionsDropdown.x}px; -->
<!--                top: {$optionsDropdown.y}px;" -->
<!--     > -->
<!--         <button onclick={() => handleOptionClick("Enzyme", body)}>Enzyme</button -->
<!--         > -->
<!--         <button onclick={() => handleOptionClick("Bacteria", body)} -->
<!--             >Bacteria</button -->
<!--         > -->
<!--         <button onclick={() => handleOptionClick("Strain", body)}>Strain</button -->
<!--         > -->
<!--     </div> -->
<!-- {/if} -->

<!-- {#if $removeDropdown.visible} -->
<!--     <div -->
<!--         class="dropdown" -->
<!--         style="position: absolute; -->
<!--                left: {$removeDropdown.x}px; -->
<!--                top: {$removeDropdown.y}px;" -->
<!--     > -->
<!--         <button class="dropdown-button" onclick={() => handleRemove(body)} -->
<!--             >Remove annotation</button -->
<!--         > -->
<!--     </div> -->
<!-- {/if} -->
