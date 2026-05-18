<script lang="ts">
    import { setContext, untrack } from "svelte";
    import { beforeNavigate } from "$app/navigation";
    import { Set } from "immutable";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import type { AnnotationState } from "$lib/annotation.svelte.ts";
    import ArticleSection from "./ArticleSection.svelte";
    import SaveIndicator from "./SaveIndicator.svelte";
    import type { SaveStatus } from "./SaveIndicator.svelte";
    import {
        createDebouncedSave,
        saveAnnotationState,
    } from "$lib/utils/autosave.ts";
    import AnnotationEditor from "./AnnotationEditor.svelte";
    import RelationEditor from "./RelationEditor.svelte";
    import type { EditorState, Reference } from "$lib/types.ts";

    interface Props {
        initialState: AnnotationState;
    }

    let { initialState }: Props = $props();

    let editorState = $state<EditorState>({ mode: "closed" });

    let saveStatus = $state<SaveStatus>({ type: "idle" });

    const { scheduleSave, cancelPending } = createDebouncedSave(2000);

    let hasMounted = false;
    $effect(() => {
        const _entities = initialState.entities;
        const _pointers = initialState.pointers;
        const _relations = initialState.relations;
        const _completed = initialState.completed;

        if (!hasMounted) {
            hasMounted = true;
            return;
        }

        saveStatus = { type: "saving" };

        scheduleSave(initialState).then((result) => {
            if (result.success) {
                saveStatus = { type: "saved", timestamp: new Date() };
            } else {
                saveStatus = {
                    type: "error",
                    message: result.error || "Unknown error",
                };
            }
        });
    });

    beforeNavigate(() => {
        cancelPending();
        saveAnnotationState(initialState);
    });

    function handleRetry() {
        saveStatus = { type: "saving" };
        scheduleSave(initialState).then((result) => {
            if (result.success) {
                saveStatus = { type: "saved", timestamp: new Date() };
            } else {
                saveStatus = {
                    type: "error",
                    message: result.error || "Unknown error",
                };
            }
        });
    }

    const reference: Reference | undefined = untrack(
        () => initialState.reference,
    );

    function abstractNeedsTitle(html: string): boolean {
        const text = html.replace(/<[^>]+>/g, "").trimStart();
        return !text.toLowerCase().startsWith("abstract");
    }

    untrack(() => {
        const validEntityIds = new globalThis.Set(initialState.entities.keys());
        const relationsArray = initialState.relations.toArray();
        const validRelations = relationsArray.filter(
            (relation) =>
                validEntityIds.has(relation.subject) &&
                validEntityIds.has(relation.object),
        );
        if (validRelations.length < relationsArray.length) {
            initialState.relations = Set(validRelations);
        }
        setContext("annotationState", initialState);
    });
    setContext("editorState", {
        get value() {
            return editorState;
        },
        set value(s: EditorState) {
            editorState = s;
        },
    });
</script>

<div id="container">
    <div id="chunk">
        <div class="reference-meta">
            <h1>{reference.title}</h1>
            <p class="meta-line">
                {reference.authors} · {reference.year}
                {#if reference.pubmed_id}
                    · PMID {reference.pubmed_id}
                {/if}
            </p>
        </div>
        {#if reference?.abstract}
            {#if abstractNeedsTitle(reference.abstract)}
                <h2 class="section-heading">Abstract</h2>
            {/if}
            <ArticleSection html={reference.abstract} field="abstract" />
        {/if}
        <ArticleSection html={reference?.body} field="body" />
    </div>

    <div id="sidebar-col">
        <div id="sidebar">
            <div id="summary">
                <Summary />
            </div>

            <div id="relations">
                <Relations />
            </div>
        </div>
    </div>
</div>

<AnnotationEditor bind:editorState />
<RelationEditor bind:editorState />

<SaveIndicator status={saveStatus} onRetry={handleRetry} />
