<script lang="ts">
    import Card, { Content } from "@smui/card";
    import { getContext, onMount } from "svelte";
    import type { Pointer, Entity } from "$lib/types.ts";
    import { AnnotationState } from "$lib/annotation.svelte";
    import type { SvelteMap } from "svelte/reactivity";
    import { getContrastColor, getLabelColor } from "$lib/utils.ts";
    import LabelDropdown from "./LabelDropdown.svelte";

    interface Props {
        fragment: DocumentFragment;
        pointer_id: number;
    }
    const { fragment, pointer_id }: Props = $props();
    const annState = getContext<AnnotationState>("annotationState");
    const dropdownState = getContext<{
        isOpen: boolean;
        position: { top: number; left: number };
        triggerElement: HTMLElement | null;
    }>("dropdownState");

    let resourceLabel = $derived.by(() => {
        const pointer = annState.pointer(pointer_id);
        if (!pointer) return "";
        const entity = annState.entity(pointer.entity_id);
        return entity?.kind ?? "";
    });
    let labelColor = $derived(getLabelColor(resourceLabel));
    let textColor = $derived(getContrastColor(labelColor));

    let mountpoint: HTMLSpanElement;
    let labelButton: HTMLButtonElement;

    function deleteAnnotation() {
        annState.delete(pointer_id);
        // Re-render happens automatically via ArticleBody's derived annotationData
    }

    function toggleDropdown() {
        if (
            dropdownState.isOpen &&
            dropdownState.triggerElement === labelButton
        ) {
            // If already open for this button, close it
            dropdownState.isOpen = false;
            dropdownState.triggerElement = null;
        } else {
            // Open dropdown for this button
            if (labelButton) {
                const rect = labelButton.getBoundingClientRect();
                dropdownState.position = {
                    top: rect.bottom + window.scrollY,
                    left: rect.left + window.scrollX,
                };
                dropdownState.triggerElement = labelButton;
                dropdownState.isOpen = true;
            }
        }
    }

    function handleLabelSelect(label: string) {
        // Find the pointer entity and update its kind
        const pointerData = pointers.get(pointer_id);
        if (pointerData) {
            const entity = entities.get(pointerData.entity_id);
            if (entity) {
                // Create new entity object to trigger reactivity
                entities.set(pointerData.entity_id, { ...entity, kind: label });
            }
        }
    }

    onMount(() => {
        if (mountpoint && fragment) {
            mountpoint.append(fragment);
        }
    });
</script>

<Card style="display: inline-block; position: relative; line-height: 1.7;">
    <Content>
        <ruby style:ruby-position="under"
            ><ruby style:ruby-position="over"
                ><span
                    bind:this={mountpoint}
                    class={["badge"]}
                    style:border={`3px solid ${labelColor};`}
                ></span>
                <rp>(</rp><rt class="delete-button-rt">
                    <button
                        class={["btn rounded primary tiny"]}
                        style:background-color={labelColor}
                        style:color={textColor}
                        aria-label={`Delete annotation ${fragment.textContent || ""}`}
                        aria-controls={pointer_id}
                        onclick={deleteAnnotation}>✕</button
                    >
                </rt><rp>)</rp></ruby
            >
            <rp>(</rp><rp>)</rp><rt class="label-button-rt"
                ><button
                    bind:this={labelButton}
                    class={["btn rounded primary tiny"]}
                    style:background-color={labelColor}
                    style:color={textColor}
                    onclick={toggleDropdown}
                    aria-haspopup="listbox"
                    aria-expanded={dropdownState.isOpen &&
                        dropdownState.triggerElement === labelButton}
                    >{resourceLabel}</button
                ></rt
            ><ruby> </ruby>
        </ruby></Content
    >
</Card>

{#if dropdownState.isOpen && dropdownState.triggerElement === labelButton}
    <LabelDropdown onSelect={handleLabelSelect} currentLabel={resourceLabel} />
{/if}

<style>
    :global(.smui-card__content) {
        padding-top: 0;
        padding-bottom: 0;
    }
</style>
