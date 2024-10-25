<script lang="ts">
    import { getContext, mount } from "svelte";
    import {
        handleOptionClick,
        handleTextSelection,
        handleRemove,
        handleKeyPress,
    } from "$lib/handlers.ts";
    import { optionsDropdown, removeDropdown } from "$lib/dropdown.ts";
    import type { bodyStore } from "$lib/body.svelte.ts";
    import ChunkButton from "$lib/components/ChunkButton.svelte";
    import { isValidEntitySpan } from "$lib/utils";

    const body: bodyStore = getContext("body");

    let content: Element;

    $effect(() => {
        if (body.content && content) {
            const spans = Array.from(content.querySelectorAll("span")).filter(
                (span) =>
                    span.firstChild?.nodeName !== "BUTTON" &&
                    isValidEntitySpan(span),
            );

            spans.forEach((span) => {
                const spanid = span.id as string;
                const name = span.textContent || "";
                span.textContent = "";
                mount(ChunkButton, {
                    target: span,
                    props: { spanid, name },
                    context: new Map([["body", body]]),
                });
            });
        }
    });
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    class="chunk-body"
    onmouseup={handleTextSelection}
    prefix={body.content?.getAttribute("prefix")}
    bind:this={content}
>
    {@html body.content?.innerHTML}
</div>

<svelte:window onkeyup={handleKeyPress} />

{#if $optionsDropdown.visible}
    <div
        class="dropdown"
        style="position: absolute;
               left: {$optionsDropdown.x}px;
               top: {$optionsDropdown.y}px;"
    >
        <button onclick={() => handleOptionClick("Enzyme", body)}>Enzyme</button
        >
        <button onclick={() => handleOptionClick("Bacteria", body)}
            >Bacteria</button
        >
        <button onclick={() => handleOptionClick("Strain", body)}>Strain</button
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
        <button class="dropdown-button" onclick={() => handleRemove(body)}
            >Remove annotation</button
        >
    </div>
{/if}
