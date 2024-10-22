<script lang="ts">
    import { getContext, onMount } from "svelte";
    import ResourceButton from "$lib/components/ResourceButton.svelte";
    import type { bodyStore } from "$lib/body.ts";
    import type { Readable } from "svelte/store";
    import type { Resource } from "$lib/resources";

    const body: bodyStore = getContext("body");
    let resources: Readable<Map<string, Resource>>;
    let classes: Set<string>;

    function plural(singular: string): string {
        if (singular === "Bacteria") {
            return singular;
        } else {
            return singular + "s";
        }
    }

    onMount(() => {
        resources = body?.resources;
        classes = body?.classes;
    });
</script>

{#if resources}
    <h2>Entities</h2>

    {#each classes as label}
        <h4>{plural(label.split(":")[1])}</h4>
        {#each $resources.entries() as [key, resource]}
            {#if resource.label === label}
                {resource.name}
                <ResourceButton {key} {resource} />
            {/if}
        {/each}
    {/each}
{/if}
