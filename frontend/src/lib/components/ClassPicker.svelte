<script lang="ts">
    import type { KindOption } from "$lib/api.ts";

    interface Props {
        value: string;
        options: KindOption[];
        id?: string;
    }

    let { value = $bindable(), options, id }: Props = $props();

    let query = $state("");
    let open = $state(false);

    // Keep the displayed query in sync when value is set externally
    $effect(() => {
        const found = options.find((o) => o.curie === value);
        query = found ? `${found.label} (${found.curie})` : value;
    });

    const filtered = $derived(
        query.length === 0
            ? options
            : options.filter(
                  (o) =>
                      o.label.toLowerCase().includes(query.toLowerCase()) ||
                      o.curie.toLowerCase().includes(query.toLowerCase()),
              ),
    );

    function select(opt: KindOption) {
        value = opt.curie;
        open = false;
    }

    function handleInput() {
        // If the user edits away from the current selection, clear the value
        const found = options.find((o) => o.curie === value);
        if (found && query !== `${found.label} (${found.curie})`) {
            value = "";
        }
        open = true;
    }
</script>

<div class="class-picker">
    <input
        {id}
        type="text"
        bind:value={query}
        oninput={handleInput}
        onfocus={() => (open = true)}
        onblur={() => setTimeout(() => (open = false), 150)}
        placeholder="Search class…"
        autocomplete="off"
    />
    {#if open && filtered.length > 0}
        <ul class="dropdown" role="listbox">
            {#each filtered as opt}
                <li role="option" aria-selected={opt.curie === value}>
                    <!-- onmousedown prevents blur from firing before click -->
                    <button type="button" onmousedown={(e) => { e.preventDefault(); select(opt); }}>
                        <span class="opt-label">{opt.label}</span>
                        <span class="opt-curie">{opt.curie}</span>
                    </button>
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    .class-picker {
        position: relative;
    }

    .class-picker input {
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        box-sizing: border-box;
    }

    .dropdown {
        position: absolute;
        z-index: 100;
        top: calc(100% + 2px);
        left: 0;
        right: 0;
        list-style: none;
        margin: 0;
        padding: 0;
        background: #fff;
        border: 1px solid #ccc;
        border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        max-height: 200px;
        overflow-y: auto;
    }

    .dropdown li button {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
        width: 100%;
        padding: 0.4rem 0.6rem;
        background: none;
        border: none;
        cursor: pointer;
        text-align: left;
        font-size: 0.875rem;
    }

    .dropdown li button:hover,
    .dropdown li[aria-selected="true"] button {
        background: #f0f0f0;
    }

    .opt-label {
        font-weight: 500;
        flex: 1;
    }

    .opt-curie {
        font-size: 0.75rem;
        color: #888;
        font-family: monospace;
    }
</style>
