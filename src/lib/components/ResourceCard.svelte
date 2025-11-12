<script lang="ts">
    import Card, { Content } from "@smui/card";
    import { getContext, setContext, onMount } from "svelte";
    import type { Pointer, Entity } from "$lib/types.ts";
    import type { SvelteMap } from "svelte/reactivity";
    import { getContrastColor, getLabelColor } from "$lib/utils.ts";

    interface Props {
        fragment: DocumentFragment;
        pointer_id: number;
    }
    const { fragment, pointer_id }: Props = $props();
    const pointers = getContext<SvelteMap<number, Pointer>>("pointers");
    const entities = getContext<SvelteMap<string, Entity>>("entities");
    const activeMenuId = getContext<{ value: number | null }>("activeMenuId");

    let resourceLabel = $derived(
        entities.get(pointers.get(pointer_id).entity_id).kind,
    );
    let labelColor = $derived(getLabelColor(resourceLabel));
    let textColor = $derived(getContrastColor(labelColor));

    let mountpoint: HTMLSpanElement;
    let buttonMountpoint: HTMLSpanElement;
    let button: HTMLButtonElement;
    let menuElement: HTMLDivElement;
    let labelButton: HTMLButtonElement;
    let dropdownOpen = $state(false);
    let searchInput = $state("");
    let dropdownElement: HTMLDivElement;
    let dropdownPosition = $state({ top: 0, left: 0 });

    // Available label options
    const allLabels = ["d3o:Strain", "d3o:Bacteria", "d3o:Enzyme"];

    // Filtered labels based on search input
    let filteredLabels = $derived(
        allLabels
            .filter((label) =>
                label.toLowerCase().includes(searchInput.toLowerCase()),
            )
            .slice(0, 5),
    );

    function deleteAnnotation() {
        pointers.delete(pointer_id);
    }

    function toggleDropdown() {
        dropdownOpen = !dropdownOpen;
        if (dropdownOpen) {
            searchInput = "";
            // Calculate position relative to the label button
            if (labelButton) {
                const rect = labelButton.getBoundingClientRect();
                dropdownPosition = {
                    top: rect.bottom + window.scrollY,
                    left: rect.left + window.scrollX,
                };
            }
            // Focus the input when opening
            setTimeout(() => {
                const input = dropdownElement?.querySelector("input");
                input?.focus();
            }, 0);
        }
    }

    function selectLabel(label: string) {
        // Find the pointer entity and update its kind
        const pointerData = pointers.get(pointer_id);
        if (pointerData) {
            const entity = entities.get(pointerData.entity_id);
            if (entity) {
                // Create new entity object to trigger reactivity
                entities.set(pointerData.entity_id, { ...entity, kind: label });
            }
        }
        dropdownOpen = false;
        searchInput = "";
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            dropdownOpen = false;
            searchInput = "";
        } else if (
            event.key === "Enter" &&
            searchInput &&
            filteredLabels.length > 0
        ) {
            selectLabel(filteredLabels[0]);
        }
    }

    // Close dropdown when clicking outside
    function handleClickOutside(event: MouseEvent) {
        if (
            dropdownOpen &&
            dropdownElement &&
            !dropdownElement.contains(event.target as Node) &&
            labelButton &&
            !labelButton.contains(event.target as Node)
        ) {
            dropdownOpen = false;
            searchInput = "";
        }
    }

    onMount(() => {
        if (mountpoint && fragment) {
            const highlightText = fragment.textContent || "";
            mountpoint.append(fragment);
        }

        document.addEventListener("click", handleClickOutside);
        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    });
</script>

<Card style="display: inline-block; position: relative;">
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
                        bind:this={buttonMountpoint}
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
                    aria-expanded={dropdownOpen}>{resourceLabel}</button
                ></rt
            ><ruby> </ruby>
        </ruby></Content
    >
</Card>

{#if dropdownOpen}
    <div
        bind:this={dropdownElement}
        class="label-dropdown"
        role="listbox"
        onkeydown={handleKeydown}
        style:top="{dropdownPosition.top}px"
        style:left="{dropdownPosition.left}px"
    >
        <input
            type="text"
            bind:value={searchInput}
            placeholder="Search or type label..."
            class="label-search-input"
            aria-label="Search labels"
        />
        <div class="label-options">
            {#each filteredLabels as label}
                <button
                    class="label-option"
                    onclick={() => selectLabel(label)}
                    role="option"
                    aria-selected={label === resourceLabel}
                >
                    {label}
                </button>
            {/each}
            {#if filteredLabels.length === 0 && searchInput}
                <span class="label-option">Label not found</span>
            {/if}
        </div>
    </div>
{/if}
