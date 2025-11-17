<script lang="ts">
    import { getContext, onMount } from "svelte";

    interface Props {
        onSelect: (label: string) => void;
        currentLabel?: string;
    }

    const { onSelect, currentLabel }: Props = $props();
    const dropdownState = getContext<{
        isOpen: boolean;
        position: { top: number; left: number };
        triggerElement: HTMLElement | null;
    }>("dropdownState");

    let searchInput = $state("");
    let dropdownElement: HTMLDivElement;

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

    function selectLabel(label: string) {
        onSelect(label);
        closeDropdown();
    }

    function closeDropdown() {
        dropdownState.isOpen = false;
        searchInput = "";
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === "Escape") {
            closeDropdown();
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
            dropdownElement &&
            !dropdownElement.contains(event.target as Node)
        ) {
            closeDropdown();
        }
    }

    $effect(() => {
        if (dropdownState.isOpen) {
            searchInput = "";
            // Focus the input when opening
            setTimeout(() => {
                const input = dropdownElement?.querySelector("input");
                input?.focus();
            }, 0);

            // Add click listener with a small delay to prevent immediate closure
            const timeoutId = setTimeout(() => {
                document.addEventListener("click", handleClickOutside, true);
            }, 100);

            return () => {
                clearTimeout(timeoutId);
                document.removeEventListener("click", handleClickOutside, true);
            };
        }
    });
</script>

{#if dropdownState.isOpen}
    <div
        bind:this={dropdownElement}
        class="label-dropdown"
        role="listbox"
        onkeydown={handleKeydown}
        style:top="{dropdownState.position.top}px"
        style:left="{dropdownState.position.left}px"
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
                    aria-selected={label === currentLabel}
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
