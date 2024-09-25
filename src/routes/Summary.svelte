<script lang="ts">
    import {
        bacteriaLabel,
        enzymeLabel,
        strainLabel,
        resources,
    } from "$lib/resources.ts";
    import { derived } from "svelte/store";
    import type { Readable } from "svelte/store";
    import { dragStart, dragOver, handleDrop } from "$lib/handlers.ts";
    import { onMount } from "svelte";

    function plural(singular: string): string {
        if (singular === "Bacteria") {
            return singular;
        } else {
            return singular + "s";
        }
    }

    const labels = [enzymeLabel, strainLabel, bacteriaLabel];

    type labelToResources = Map<string, Array<string>>;
    const classes: Readable<labelToResources> = derived(
        resources,
        ($resources) => {
            const m = new Map();
            labels.forEach((label) =>
                m.set(
                    label,
                    Array.from($resources.values()).filter(
                        (res) => res.label === label,
                    ),
                ),
            );

            return m;
        },
    );
</script>

<h2>Entities</h2>

{#each $classes as [label, resources]}
    {#if resources.length}
        <h3>{plural(label.split(":")[1])}</h3>
        {#each resources as resource}
            {#if resource.count}
                <button
                    type="button"
                    class="entity entitySummary"
                    resource={resource.id}
                    typeof={label}
                    draggable="true"
                    on:dragstart={dragStart}
                    on:dragover={dragOver}
                    on:drop={handleDrop}
                >
                    {resource.name}
                </button>
            {/if}
        {/each}
    {/if}
{/each}
