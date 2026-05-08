<script lang="ts">
    import { getContext, onMount } from "svelte";
    import { browser } from "$app/environment";
    import { AnnotationState, extractSentence } from "$lib/annotation.svelte";
    import type {
        EditorState,
        EntitySearchResult,
        Pointer,
    } from "$lib/types.ts";
    import { searchEntities, fetchEntityTypes } from "$lib/api.ts";
    import type { KindOption } from "$lib/api.ts";
    import ClassPicker from "$lib/components/ClassPicker.svelte";
    import DOMPurify from "dompurify";
    import { Map as ImmutableMap } from "immutable";

    interface Props {
        editorState: EditorState;
    }

    let { editorState = $bindable() }: Props = $props();

    const annotationState = getContext<AnnotationState>("annotationState");

    let availableKinds = $state<KindOption[]>([]);
    onMount(() => {
        fetchEntityTypes().then((kinds) => (availableKinds = kinds));
    });

    const sortedKinds = $derived.by(() => {
        const freq = new Map<string, number>();
        for (const entity of annotationState.entities.values()) {
            if (entity.kind)
                freq.set(entity.kind, (freq.get(entity.kind) ?? 0) + 1);
        }
        return [...availableKinds].sort((a, b) => {
            const diff = (freq.get(b.curie) ?? 0) - (freq.get(a.curie) ?? 0);
            return diff !== 0 ? diff : a.label.localeCompare(b.label);
        });
    });

    let dialog: HTMLDialogElement;

    const pointer = $derived(
        editorState.mode === "edit-pointer"
            ? annotationState.pointer(editorState.pointerId)
            : null,
    );

    const entity = $derived.by(() => {
        if (editorState.mode === "edit-pointer" && pointer) {
            return annotationState.entity(pointer.entity_id);
        }
        if (editorState.mode === "edit-entity") {
            return annotationState.entity(editorState.entityId);
        }
        return null;
    });

    const abstractPlainText = $derived.by(() => {
        if (!browser) return "";
        const abstract = annotationState.reference.abstract;
        if (!abstract) return "";
        const div = document.createElement("div");
        div.innerHTML = DOMPurify.sanitize(abstract);
        return div.textContent || "";
    });

    const bodyPlainText = $derived.by(() => {
        if (!browser) return "";
        const body = annotationState.reference.body;
        if (!body) return "";
        const div = document.createElement("div");
        div.innerHTML = DOMPurify.sanitize(body);
        return div.textContent || "";
    });

    function plainTextForField(field: "abstract" | "body"): string {
        return field === "abstract" ? abstractPlainText : bodyPlainText;
    }

    const sentenceData = $derived.by(() => {
        if (editorState.mode === "create") {
            const pt = plainTextForField(editorState.field);
            const { text } = extractSentence(pt, editorState.offset);
            const relOffset = editorState.offset - editorState.sentenceStart;
            return {
                sentence: text,
                highlightStart: relOffset,
                highlightEnd: relOffset + editorState.length,
            };
        }
        if (editorState.mode === "edit-pointer" && pointer) {
            const pt = plainTextForField(pointer.field);
            const { text } = extractSentence(pt, pointer.offset);
            const relOffset = pointer.offset - editorState.sentenceStart;
            return {
                sentence: text,
                highlightStart: relOffset,
                highlightEnd: relOffset + pointer.length,
            };
        }
        return null;
    });

    const highlightedText = $derived.by(() => {
        if (!sentenceData) return "";
        return sentenceData.sentence.slice(
            sentenceData.highlightStart,
            sentenceData.highlightEnd,
        );
    });

    let selectedKind = $state("");
    let preferredName = $state("");
    let newSynonym = $state("");
    let synonymList = $state<string[]>([]);
    let uriValue = $state("");

    let createTab = $state<"existing" | "new">("existing");
    let entitySearch = $state("");
    let selectedExistingEntityId = $state<string | null>(null);

    let sentenceContainer = $state<HTMLDivElement | undefined>(undefined);
    let pendingRange = $state<{ offset: number; length: number } | null>(null);

    let collapsedMentions = $state<Set<number>>(new Set());

    const isMyMode = $derived(
        editorState.mode === "create" ||
            editorState.mode === "edit-pointer" ||
            editorState.mode === "edit-entity",
    );

    $effect(() => {
        if (!dialog) return;
        if (!isMyMode) {
            dialog.close();
        } else {
            resetForm();
            dialog.showModal();
        }
    });

    function resetForm() {
        pendingRange = null;
        collapsedMentions = new Set();
        newSynonym = "";
        entitySearch = "";
        selectedExistingEntityId = null;
        createTab = "existing";

        if (editorState.mode === "create") {
            selectedKind = "";
            preferredName = highlightedText;
            synonymList = [highlightedText];
            uriValue = "";
        } else if (editorState.mode === "edit-pointer" && entity) {
            selectedKind = entity.kind;
            preferredName = entity.preferred_name;
            synonymList = entity.synonyms.toArray();
            uriValue = entity.uri ?? "";
        } else if (editorState.mode === "edit-entity" && entity) {
            selectedKind = entity.kind;
            preferredName = entity.preferred_name;
            synonymList = entity.synonyms.toArray();
            uriValue = entity.uri ?? "";
        }
    }

    function close() {
        editorState = { mode: "closed" };
    }

    function buildSentenceHTML(data: typeof sentenceData): string {
        if (!data) return "";
        const { sentence, highlightStart, highlightEnd } = data;
        const before = sentence.slice(0, highlightStart);
        const highlight = sentence.slice(highlightStart, highlightEnd);
        const after = sentence.slice(highlightEnd);
        return (
            DOMPurify.sanitize(before) +
            `<mark>${DOMPurify.sanitize(highlight)}</mark>` +
            DOMPurify.sanitize(after)
        );
    }

    function buildMentionSentenceHTML(p: Pointer): string {
        const pt = plainTextForField(p.field);
        const { text, start } = extractSentence(pt, p.offset);
        const relOffset = p.offset - start;
        const before = text.slice(0, relOffset);
        const highlight = text.slice(relOffset, relOffset + p.length);
        const after = text.slice(relOffset + p.length);
        return (
            DOMPurify.sanitize(before) +
            `<mark>${DOMPurify.sanitize(highlight)}</mark>` +
            DOMPurify.sanitize(after)
        );
    }

    function handleSentenceMouseUp() {
        const selection = window.getSelection();
        if (!selection || selection.isCollapsed || !sentenceContainer) return;
        const range = selection.getRangeAt(0);
        if (!sentenceContainer.contains(range.commonAncestorContainer)) return;

        const walker = sentenceContainer.ownerDocument.createTreeWalker(
            sentenceContainer,
            NodeFilter.SHOW_TEXT,
        );
        let offset = 0;
        let node: Node | null;
        while ((node = walker.nextNode())) {
            if (node === range.startContainer) {
                const rawText = range.toString();
                const trimmedText = rawText.trim();
                const leadingSpaces = rawText.length - rawText.trimStart().length;
                const selectionOffset = offset + range.startOffset + leadingSpaces;
                const length = trimmedText.length;
                if (length > 0) {
                    pendingRange = { offset: selectionOffset, length };
                }
                break;
            }
            offset += (node.textContent || "").length;
        }
        selection.removeAllRanges();
    }

    let searchResults = $state<EntitySearchResult[]>(
        annotationState.entities
            .valueSeq()
            .map((e) => ({
                entity_id: e.entity_id,
                preferred_name: e.preferred_name,
                kind: e.kind,
                uri: e.uri ?? undefined,
                confirmed: e.confirmed,
            }))
            .toArray(),
    );
    let searchLoading = $state(false);

    $effect(() => {
        const q = entitySearch;
        if (q.length < 2) {
            searchResults = annotationState.entities
                .valueSeq()
                .map((e) => ({
                    entity_id: e.entity_id,
                    preferred_name: e.preferred_name,
                    kind: e.kind,
                    uri: e.uri ?? undefined,
                    confirmed: e.confirmed,
                }))
                .toArray();
            searchLoading = false;
            return;
        }
        searchLoading = true;
        const controller = new AbortController();
        const timer = setTimeout(() => {
            searchEntities(q, 20, undefined, controller.signal).then((results) => {
                searchResults = results;
                searchLoading = false;
            }).catch(() => {});
        }, 300);
        return () => {
            clearTimeout(timer);
            controller.abort();
        };
    });

    function confirmCreate() {
        if (editorState.mode !== "create") return;
        const { offset, length, field } = editorState;
        if (createTab === "existing") {
            if (!selectedExistingEntityId) return;
            const result = searchResults.find(
                (e) => e.entity_id === selectedExistingEntityId,
            );
            annotationState.addWithId(
                selectedExistingEntityId,
                result?.kind ?? "",
                result?.preferred_name ?? "",
                [{ offset, length }],
                result?.confirmed ?? true,
                field,
            );
        } else {
            if (!selectedKind || !preferredName.trim()) return;
            annotationState.add(selectedKind, preferredName.trim(), [{ offset, length }], field);
        }
        close();
    }

    function confirmEditPointer() {
        if (!pointer || !entity) return;
        const entityId = pointer.entity_id;

        if (pendingRange && editorState.mode === "edit-pointer") {
            const absOffset = editorState.sentenceStart + pendingRange.offset;
            const newText = plainTextForField(pointer.field)
                .slice(absOffset, absOffset + pendingRange.length)
                .trim();
            if (newText && !synonymList.includes(newText))
                synonymList = [...synonymList, newText];
            annotationState.updatePointerOffsets(
                editorState.pointerId,
                absOffset,
                pendingRange.length,
            );
        }

        annotationState.updateEntityKind(entityId, selectedKind);
        annotationState.updateEntityPreferredName(
            entityId,
            preferredName.trim(),
        );
        if (uriValue.trim())
            annotationState.updateEntityUri(entityId, uriValue.trim());

        const currentSynonyms = entity.synonyms;
        const targetSynonyms = new Set(synonymList);
        for (const s of targetSynonyms) {
            if (!currentSynonyms.has(s))
                annotationState.addSynonym(entityId, s);
        }
        for (const s of currentSynonyms) {
            if (!targetSynonyms.has(s))
                annotationState.removeSynonym(entityId, s);
        }

        close();
    }

    function confirmEditEntity() {
        const state = editorState;
        if (!entity || state.mode !== "edit-entity") return;
        const entityId = state.entityId;

        annotationState.updateEntityKind(entityId, selectedKind);
        annotationState.updateEntityPreferredName(
            entityId,
            preferredName.trim(),
        );
        if (uriValue.trim())
            annotationState.updateEntityUri(entityId, uriValue.trim());

        const currentSynonyms = entity.synonyms;
        const targetSynonyms = new Set(synonymList);
        for (const s of targetSynonyms) {
            if (!currentSynonyms.has(s))
                annotationState.addSynonym(entityId, s);
        }
        for (const s of currentSynonyms) {
            if (!targetSynonyms.has(s))
                annotationState.removeSynonym(entityId, s);
        }

        close();
    }

    function deletePointer() {
        if (editorState.mode !== "edit-pointer") return;
        annotationState.delete(editorState.pointerId);
        close();
    }

    function deleteEntity() {
        const state = editorState;
        if (state.mode !== "edit-entity") return;
        annotationState.deleteEntity(state.entityId);
        close();
    }

    function addSynonym() {
        const s = newSynonym.trim();
        if (s && !synonymList.includes(s)) {
            synonymList = [...synonymList, s];
        }
        newSynonym = "";
    }

    function removeSynonym(s: string) {
        synonymList = synonymList.filter((x) => x !== s);
    }

    function toggleMention(i: number) {
        const next = new Set(collapsedMentions);
        if (next.has(i)) next.delete(i);
        else next.add(i);
        collapsedMentions = next;
    }

    const entityPointerEntries: ImmutableMap<string, Pointer> = $derived.by(
        () => {
            const state = editorState;
            if (state.mode !== "edit-entity") return ImmutableMap();
            return annotationState.pointers.filter(
                (p) => p.entity_id === state.entityId,
            );
        },
    );
</script>

<dialog
    bind:this={dialog}
    onclose={close}
    onkeydown={(e) => e.key === "Escape" && close()}
    class="annotation-editor"
>
    {#if editorState.mode === "create"}
        <h2>New Annotation</h2>

        {#if sentenceData}
            <div class="sentence-preview">
                <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                {@html buildSentenceHTML(sentenceData)}
            </div>
        {/if}

        <div class="tabs">
            <button
                class:active={createTab === "existing"}
                onclick={() => {
                    createTab = "existing";
                    selectedExistingEntityId = null;
                }}
            >
                Add to existing entity
            </button>
            <button
                class:active={createTab === "new"}
                onclick={() => (createTab = "new")}
            >
                New entity
            </button>
        </div>

        {#if createTab === "existing"}
            <input
                class="search-input"
                type="text"
                placeholder="Search entities…"
                bind:value={entitySearch}
            />
            <ul class="entity-list">
                {#if searchLoading}
                    <li class="empty">Searching…</li>
                {:else}
                    {#each searchResults as e (e.entity_id)}
                        <li>
                            <label class="entity-option">
                                <input
                                    type="radio"
                                    name="existing-entity"
                                    value={e.entity_id}
                                    bind:group={selectedExistingEntityId}
                                />
                                <span class="entity-name"
                                    >{e.preferred_name}</span
                                >
                                {#if !e.confirmed}<span class="entity-proposed"
                                        >proposed</span
                                    >{/if}
                                <span class="entity-kind">{e.kind}</span>
                            </label>
                        </li>
                    {/each}
                    {#if searchResults.length === 0}
                        <li class="empty">No entities match.</li>
                    {/if}
                {/if}
            </ul>
        {:else}
            <div class="field">
                <label for="preferred-name-create">Preferred name</label>
                <input
                    id="preferred-name-create"
                    type="text"
                    bind:value={preferredName}
                />
            </div>

            <div class="field">
                <label for="kind-create">Class</label>
                <ClassPicker
                    id="kind-create"
                    bind:value={selectedKind}
                    options={sortedKinds}
                />
            </div>
        {/if}

        <div class="actions">
            <button class="btn primary filled" onclick={confirmCreate}>Confirm</button>
            <button class="btn secondary" onclick={close}>Cancel</button>
        </div>
    {:else if editorState.mode === "edit-pointer"}
        <h2>Edit Annotation</h2>

        {#if sentenceData}
            <p class="hint">
                Select text below to change the highlight boundary.
            </p>
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div
                class="sentence-preview selectable"
                bind:this={sentenceContainer}
                onmouseup={handleSentenceMouseUp}
            >
                {#if pendingRange}
                    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                    {@html DOMPurify.sanitize(
                        sentenceData.sentence.slice(0, pendingRange.offset) +
                            "<mark>" +
                            sentenceData.sentence.slice(
                                pendingRange.offset,
                                pendingRange.offset + pendingRange.length,
                            ) +
                            "</mark>" +
                            sentenceData.sentence.slice(
                                pendingRange.offset + pendingRange.length,
                            ),
                    )}
                {:else}
                    <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                    {@html buildSentenceHTML(sentenceData)}
                {/if}
            </div>
        {/if}

        <div class="field">
            <label for="preferred-name-ep">Preferred name</label>
            <input
                id="preferred-name-ep"
                type="text"
                bind:value={preferredName}
            />
        </div>

        <div class="field">
            <label for="uri-ep">URI</label>
            <input
                id="uri-ep"
                type="text"
                bind:value={uriValue}
                placeholder="optional"
            />
        </div>

        <div class="field">
            <label for="kind-ep">Class</label>
            <ClassPicker
                id="kind-ep"
                bind:value={selectedKind}
                options={sortedKinds}
            />
        </div>

        <div class="field">
            <p class="field-label">Synonyms</p>
            <ul class="synonym-list">
                {#each synonymList as s (s)}
                    <li>
                        <span>{s}</span>
                        <button
                            class="btn-remove"
                            onclick={() => removeSynonym(s)}
                            aria-label="Remove synonym">×</button
                        >
                    </li>
                {/each}
            </ul>
            <div class="synonym-add">
                <input
                    type="text"
                    bind:value={newSynonym}
                    placeholder="Add synonym…"
                    onkeydown={(e) => e.key === "Enter" && addSynonym()}
                />
                <button class="btn secondary" onclick={addSynonym}>Add</button>
            </div>
        </div>

        <div class="actions">
            <button class="btn primary filled" onclick={confirmEditPointer}
                >Confirm</button
            >
            <button class="btn danger filled" style="margin-left: auto" onclick={deletePointer}
                >Delete highlight</button
            >
            <button class="btn secondary" onclick={close}>Cancel</button>
        </div>
    {:else if editorState.mode === "edit-entity"}
        <h2>Edit Entity</h2>

        <div class="field">
            <label for="preferred-name-ee">Preferred name</label>
            <input
                id="preferred-name-ee"
                type="text"
                bind:value={preferredName}
            />
        </div>

        <div class="field">
            <label for="uri-ee">URI</label>
            <input
                id="uri-ee"
                type="text"
                bind:value={uriValue}
                placeholder="optional"
            />
        </div>

        <div class="field">
            <label for="kind-ee">Class</label>
            <ClassPicker
                id="kind-ee"
                bind:value={selectedKind}
                options={sortedKinds}
            />
        </div>

        <div class="field">
            <p class="field-label">Synonyms</p>
            <ul class="synonym-list">
                {#each synonymList as s (s)}
                    <li>
                        <span>{s}</span>
                        <button
                            class="btn-remove"
                            onclick={() => removeSynonym(s)}
                            aria-label="Remove synonym">×</button
                        >
                    </li>
                {/each}
            </ul>
            <div class="synonym-add">
                <input
                    type="text"
                    bind:value={newSynonym}
                    placeholder="Add synonym…"
                    onkeydown={(e) => e.key === "Enter" && addSynonym()}
                />
                <button class="btn secondary" onclick={addSynonym}>Add</button>
            </div>
        </div>

        <div class="actions">
            <button class="btn primary filled" onclick={confirmEditEntity}
                >Confirm</button
            >
            <button class="btn danger filled" style="margin-left: auto" onclick={deleteEntity}
                >Delete entity</button
            >
            <button class="btn secondary" onclick={close}>Cancel</button>
        </div>

        <div class="mentions">
            <p class="mentions-header">
                {entityPointerEntries.count()} mention{entityPointerEntries.count() !==
                1
                    ? "s"
                    : ""} in text
            </p>
            {#each entityPointerEntries as [key, p], i (key)}
                <div class="mention">
                    <button
                        class="mention-toggle"
                        onclick={() => toggleMention(i)}
                    >
                        {collapsedMentions.has(i) ? "▸" : "▾"}
                        {plainTextForField(p.field).slice(p.offset, p.offset + p.length)}
                    </button>
                    {#if !collapsedMentions.has(i)}
                        <div class="sentence-preview">
                            <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                            {@html buildMentionSentenceHTML(p)}
                        </div>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}
</dialog>

<style>
    .annotation-editor {
        border: none;
        border-radius: 8px;
        padding: 1.5rem;
        width: min(560px, 90vw);
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    .annotation-editor::backdrop {
        background: rgba(0, 0, 0, 0.4);
    }

    h2 {
        margin: 0 0 1rem;
        font-size: 1.1rem;
    }

    .sentence-preview {
        background: #f5f5f5;
        border-left: 3px solid #999;
        border-radius: 4px;
        padding: 0.6rem 0.8rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        line-height: 1.5;
    }

    .sentence-preview :global(mark) {
        background: #ffe58f;
        border-radius: 2px;
        padding: 0 2px;
    }

    .selectable {
        cursor: text;
        user-select: text;
    }

    .hint {
        font-size: 0.8rem;
        color: #666;
        margin: 0 0 0.4rem;
    }

    .tabs {
        display: flex;
        gap: 0.5rem;
        margin-bottom: 1rem;
    }

    .tabs button {
        padding: 0.4rem 0.8rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        background: #f9f9f9;
        cursor: pointer;
        font-size: 0.85rem;
    }

    .tabs button.active {
        background: #333;
        color: #fff;
        border-color: #333;
    }

    .tabs button:disabled {
        opacity: 0.4;
        cursor: not-allowed;
    }

    .search-input {
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        margin-bottom: 0.5rem;
        font-size: 0.875rem;
        box-sizing: border-box;
    }

    .entity-list {
        list-style: none;
        padding: 0;
        margin: 0 0 1rem;
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid #eee;
        border-radius: 4px;
    }

    .entity-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.4rem 0.6rem;
        cursor: pointer;
    }

    .entity-option:hover {
        background: #f0f0f0;
    }

    .entity-name {
        font-weight: 500;
        flex: 1;
    }

    .entity-kind {
        font-size: 0.75rem;
        color: #777;
    }

    .entity-proposed {
        font-size: 0.7rem;
        font-weight: 600;
        color: #a06000;
        background: #fff3cd;
        border: 1px solid #f0c040;
        border-radius: 3px;
        padding: 0 0.3em;
        line-height: 1.4;
    }

    .empty {
        padding: 0.5rem 0.6rem;
        color: #888;
        font-size: 0.85rem;
    }

    .field {
        margin-bottom: 1rem;
    }

    .field label,
    .field .field-label {
        display: block;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
        color: #444;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }

    .field .field-label {
        margin-top: 0;
    }

    .field input[type="text"] {
        width: 100%;
        padding: 0.4rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        box-sizing: border-box;
    }

    .synonym-list {
        list-style: none;
        padding: 0;
        margin: 0 0 0.4rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.3rem;
    }

    .synonym-list li {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        background: #eee;
        border-radius: 4px;
        padding: 0.2rem 0.4rem;
        font-size: 0.8rem;
    }

    .btn-remove {
        background: none;
        border: none;
        cursor: pointer;
        padding: 0;
        font-size: 0.9rem;
        line-height: 1;
        color: #888;
    }

    .btn-remove:hover {
        color: #c00;
    }

    .synonym-add {
        display: flex;
        gap: 0.4rem;
    }

    .synonym-add input {
        flex: 1;
        padding: 0.35rem 0.6rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
    }

    .mentions {
        margin-bottom: 1rem;
    }

    .mentions-header {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #444;
        margin: 0 0 0.4rem;
    }

    .mention {
        margin-bottom: 0.4rem;
    }

    .mention-toggle {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 0.875rem;
        padding: 0.2rem 0;
        text-align: left;
        width: 100%;
        color: #333;
    }

    .mention-toggle:hover {
        color: #000;
    }

    .actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }

</style>
