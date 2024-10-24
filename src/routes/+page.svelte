<script lang="ts">
    import { browser } from "$app/environment";
    import { setContext, onMount } from "svelte";
    import { writable, type Writable } from "svelte/store";
    import type { PageData } from "./$types";

    import "../styles.css";
    import App from "$lib/components/App.svelte";
    import { bodyStore } from "$lib/body";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();
    const { document } = data;
    let header: Element = $state();

    let body: bodyStore = $state();

    async function parse(doc: string): Promise<void> {
        let content: Document;

        if (browser) {
            content = new DOMParser().parseFromString(doc, "text/html");
        } else {
            const { JSDOM } = await import("jsdom");
            content = new JSDOM(doc).window.document;
        }

        header = content?.querySelector(".metadata") as Element;
        const bodyEl = content?.querySelector(".chunk-body");

        if (bodyEl) {
            body = new bodyStore(bodyEl);
        }
    }

    onMount(async () => await parse(document));
</script>

{#if header && body.content}
    <App {header} bind:body />
{/if}
