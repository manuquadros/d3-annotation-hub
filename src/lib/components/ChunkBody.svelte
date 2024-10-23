<script lang="ts">
    import { getContext, onMount } from "svelte";
    import {
        handleOptionClick,
        handleTextSelection,
        handleRemove,
        handleKeyPress,
    } from "$lib/handlers.ts";
    import { optionsDropdown, removeDropdown } from "$lib/dropdown.ts";
    import type { bodyStore } from "$lib/body";
    import ChunkButton from "$lib/components/ChunkButton.svelte";

    let body: bodyStore = getContext("body");
    $: entspans = body.entspans;

    onMount(() => {
        if ($body) {
            const spans = body.spans;
            body.update((body) => {
                spans.forEach((span) => {
                    const spanid = span.id as string;
                    const name = span.textContent || "";
                    span.textContent = "";
                    new ChunkButton({
                        target: span,
                        props: { spanid, name },
                        context: new Map([["entspans", entspans]]),
                    });
                });
                return body;
            });
        }
    });

    $: bodyHTML = $body?.outerHTML || "";
</script>

<div class="chunk-body">
    <!-- on:mouseup={handleTextSelection}> -->
    {@html bodyHTML}
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
        <button class="dropdown-button" on:click={handleRemove}
            >Remove annotation</button
        >
    </div>
{/if}
