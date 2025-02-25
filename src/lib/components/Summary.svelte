<script lang="ts">
    import { getContext } from "svelte";
    import ResourceButton from "$lib/components/ResourceButton.svelte";
    import type { BodyStore } from "$lib/body.svelte.ts";

    const body: BodyStore = getContext("body");

    function plural(singular: string): string {
        if (singular === "Bacteria") {
            return singular;
        } else {
            return singular + "s";
        }
    }
</script>

{#if body.resources}
    <h2>Entities</h2>

    {#each body.classes as label}
        <h4>{plural(label.split(":")[1])}</h4>
        {#each body.resources?.values() as resource}
            {#if resource.label === label}
                <ResourceButton {resource} />
            {/if}
        {/each}
    {/each}
{/if}
