<script lang="ts">
    import { getContext, setContext, onMount } from "svelte";
    import type { SvelteMap } from "svelte/reactivity";
    import type { Pointer, Entity, DropdownState } from "$lib/types.ts";
    import { annotateHTMLString } from "$lib/annotation.ts";
    import LabelDropdown from "./LabelDropdown.svelte";
    import type { Attachment } from "svelte/attachments";

    let { body } = $props();
    const entities = getContext<SvelteMap<string, Entity>>("entities");
    const pointers = getContext<SvelteMap<number, Pointer>>("pointers");
    let dropdownState = getContext<{
        isOpen: boolean;
        position: { top: number; left: number };
        triggerElement: HTMLElement | null;
    }>("dropdownState");

    let container: HTMLDivElement;
    let selectedRange: Range | null = null;

    // Derive a snapshot of the data that changes whenever pointers or
    // entities mutate, to trigger reactivity.
    let annotationData = $derived({
        pointers: Array.from(pointers.entries()),
        entities: Array.from(entities.entries()),
    });

    const renderAnnotated: Attachment = (element: HTMLDivElement) => {
        // Access the derived value to make this reactive
        annotationData;
        annotateHTMLString(element, body, entities, pointers);
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
