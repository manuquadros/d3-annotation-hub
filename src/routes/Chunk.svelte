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

        spans.forEach((span) => {
            const type = span.getAttribute("typeof");
            const text = span.textContent;
            dispatch("entityFound", { type, text });
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
</script>

{#await promise}
    <p>Loading...</p>
{:then content}
    <div>
        {#if content}
            {@html content}
        {/if}
    </div>
{:catch error}
    <p style="color: red">{error.message}</p>
{/await}
