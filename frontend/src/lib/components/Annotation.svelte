<script lang="ts">
    import { setContext, untrack } from "svelte";
    import { beforeNavigate } from "$app/navigation";
    import { Set } from "immutable";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import type { AnnotationState } from "$lib/annotation.svelte.ts";
    import ArticleBody from "./ArticleBody.svelte";
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

    $effect(() => {
        const _entities = initialState.entities;
        const _pointers = initialState.pointers;
        const _relations = initialState.relations;
        const _completed = initialState.completed;

        let hasMounted = false;

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
    const body: string | undefined = reference?.body;

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
            console.debug("[Annotation] editorState set to", s.mode);
            editorState = s;
        },
    });
</script>

<div id="container">
    <div id="chunk">
        <div class="reference-meta">
            <h2>{reference.title}</h2>
            <p class="meta-line">
                {reference.authors} · {reference.year}
                {#if reference.pubmed_id}
                    · PMID {reference.pubmed_id}
                {/if}
            </p>
        </div>
        <ArticleBody {body} />
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
