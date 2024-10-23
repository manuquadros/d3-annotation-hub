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

    const body: bodyStore = getContext("body");
    let bodyDiv: HTMLElement;

    $: if (bodyDiv) {
        body.content.update((body) => bodyDiv);
    }

    $: entspanStore = body.entspans;
    $: entspans = $entspanStore;
    $: {
        if (body.content) {
            const spans = body.spans.filter(
                (span) => span.firstChild?.nodeName !== "BUTTON",
            );
            body.content.update((body) => {
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
    }
    $: content = body.content;
</script>

<div
    class="chunk-body"
    on:mouseup={handleTextSelection}
    prefix={$content.getAttribute("prefix")}
    bind:this={bodyDiv}
>
    {@html $content.innerHTML}
</div>

<svelte:window on:keyup|preventDefault={handleKeyPress} />

{#if $optionsDropdown.visible}
    <div
        class="dropdown"
        style="position: absolute;
               left: {$optionsDropdown.x}px;
               top: {$optionsDropdown.y}px;"
    >
        <button on:click={() => handleOptionClick("Enzyme", body)}
            >Enzyme</button
        >
        <button on:click={() => handleOptionClick("Bacteria", body)}
            >Bacteria</button
        >
        <button on:click={() => handleOptionClick("Strain", body)}
            >Strain</button
        >
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
