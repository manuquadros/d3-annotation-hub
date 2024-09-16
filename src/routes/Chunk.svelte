<script lang="ts">
    import { onMount, createEventDispatcher } from "svelte";
    const dispatch = createEventDispatcher();
    export let annotator: string = "";
    export let id: string = "";
    let promise;

    async function loadChunk() {
        let url: string;
        if (annotator && id) {
            url = `http://localhost:8000/annotation/?annotator=${annotator}&id=${id}`;
        } else if (id) {
            console.log(`loading article ${id}`);
            url = `http://localhost:8000/segment/?pmid=${id}`;
        } else {
            console.log("start and pmid are null");
            url = "http://localhost:8000/segment/";
        }
        let response = await fetch(url);
        return response.json();
    }

    function log(str: string) {
        console.log("Response data:", JSON.stringify(str, null, 2));
    }

    function processTags(content: string) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(content, "text/html");
        const spans = doc.querySelectorAll("span[typeof]");
        const resources = new Map<string, string>();

        spans.forEach((span) => {
            const type = span.getAttribute("typeof");
            const resource = span.getAttribute("resource");
            const text = span.textContent;
            const typeText = type + text!;

            if (typeText !== null && resource !== null) {
                const existentResource = resources.get(typeText);
                if (existentResource !== undefined) {
                    span.setAttribute("resource", existentResource);
                } else {
                    resources.set(typeText, resource);
                }

                dispatch("entityFound", { type, text, resource });
            }
        });

        return content;
    }

    onMount(() => {
        promise = loadChunk().then((data) => {
            if (data) {
                const content = JSON.parse(data).content;
                return processTags(content);
            }
            return null;
        });
    });

    const logHtml = (el: Element) => {
        console.log(el.innerHTML);
    };
</script>

{#await promise}
    <p>Loading...</p>
{:then content}
    <div use:logHtml>
        {#if content}
            {@html content}
        {/if}
    </div>
{:catch error}
    <p style="color: red">{error.message}</p>
{/await}
