<script lang="ts">
    import { onMount, createEventDispatcher } from "svelte";
    const dispatch = createEventDispatcher();
    export let annotator: string = "";
    export let id: string = "";
    let promise;
    let showDropdown = false;
    let dropdownPosition = { x: 0, y: 0 };
    let selectedText = "";
    const resources = new Map<string, string>();

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

    function processTags(content: string) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(content, "text/html");
        const spans = doc.querySelectorAll("span[typeof]");

        spans.forEach((span) => {
            const type = span.getAttribute("typeof");
            const resource = span.getAttribute("resource");
            const text = span.textContent;
            const typeText = type + text!;

            console.log(typeText);

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

        document.addEventListener("mouseup", handleTextSelection);
    });

    function handleTextSelection(event: MouseEvent) {
        const selection = window.getSelection();
        if (selection && !selection.isCollapsed) {
            selectedText = selection.toString().trim();
            if (selectedText) {
                showDropdown = true;
                dropdownPosition = { x: event.clientX, y: event.clientY };
            }
        } else {
            showDropdown = false;
        }
    }

    function handleOptionClick(option: string) {
        const selection = window.getSelection();
        if (selection && !selection.isCollapsed) {
            const range = selection.getRangeAt(0);
            const span = document.createElement("span");
            span.className = "entity";
            span.setAttribute("typeof", `d3o:${option}`);
            range.surroundContents(span);
            selection.removeAllRanges();
        }
        showDropdown = false;
    }
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

{#if showDropdown}
    <div
        class="dropdown"
        style="position: absolute; left: {dropdownPosition.x}px; top: {dropdownPosition.y}px;"
    >
        <button on:click={() => handleOptionClick("Enzyme")}>Enzyme</button>
        <button on:click={() => handleOptionClick("Bacteria")}>Bacteria</button>
        <button on:click={() => handleOptionClick("Strain")}>Strain</button>
    </div>
{/if}
