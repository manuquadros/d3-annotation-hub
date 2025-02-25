<script lang="ts">
    import { browser } from "$app/environment";
    import type { PageData } from "./$types";

    import "../styles.css";
    import App from "$lib/components/App.svelte";
    import { BodyStore } from "$lib/body.svelte.ts";

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
</script>

{#await parse(document)}
    <div>Loading...</div>
{:then}
    <App {header} body={new BodyStore(chunkBody)} />
{/await}
