<script lang="ts">
    import { browser } from "$app/environment";
    import type { PageData } from "./$types";

    import "../styles.css";
    import Annotation from "$lib/components/Annotation.svelte";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();

    let initialState = $derived(data.documentData);
</script>

{#if initialState}
    {#key initialState}
        <Annotation {initialState} />
    {/key}
{:else}
    <p>No references in the queue.</p>
{/if}
