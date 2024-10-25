<script lang="ts">
    import { browser } from "$app/environment";
    import { onMount } from "svelte";
    import type { PageData } from "./$types";

    import "../styles.css";
    import App from "$lib/components/App.svelte";
    import { bodyStore } from "$lib/body.svelte.ts";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();
    const { document } = data;

    // svelte-ignore non_reactive_update
    let header: Element;
    // svelte-ignore non_reactive_update
    let chunkBody: Element;

    async function parse(doc: string): Promise<void> {
        let content: Document;

        if (browser) {
            content = new DOMParser().parseFromString(doc, "text/html");
        } else {
            const { JSDOM } = await import("jsdom");
            content = new JSDOM(doc).window.document;
        }

        header = content?.querySelector(".metadata") as Element;
        chunkBody = content?.querySelector(".chunk-body") as Element;
    }

    onMount(async () => await parse(document));
</script>

{#if header && chunkBody}
    <App {header} body={new bodyStore(chunkBody)} />
{/if}
