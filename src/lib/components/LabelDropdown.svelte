<script lang="ts">
    import { getContext, onMount } from "svelte";

    interface CustomAction {
        label: string;
        handler: () => void;
    }

    interface Props {
        onSelect: (label: string) => void;
        currentLabel?: string;
        customActions?: CustomAction[];
    }

    const { onSelect, currentLabel, customActions = [] }: Props = $props();
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

    function handleCustomAction(action: CustomAction) {
        action.handler();
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
        {#if customActions.length > 0}
            <div class="custom-actions">
                {#each customActions as action}
                    <button
                        class="label-option custom-action"
                        onclick={() => handleCustomAction(action)}
                        role="option"
                    >
                        {action.label}
                    </button>
                {/each}
            </div>
            <div class="dropdown-separator"></div>
        {/if}
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

<style>
    .custom-actions {
        padding: 4px 0;
    }

    .custom-action {
        font-weight: 600;
        color: #2563eb;
    }

    .custom-action:hover {
        background-color: #eff6ff;
    }

    .dropdown-separator {
        height: 1px;
        background-color: #e5e7eb;
        margin: 4px 0;
    }
</style>
