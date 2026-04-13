<script lang="ts">
    import { setContext } from "svelte";
    import { beforeNavigate } from "$app/navigation";
    import { Set } from "immutable";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import type { AnnotationState } from "$lib/annotation.svelte.ts";
    import ArticleBody from "./ArticleBody.svelte";
    import SaveIndicator from "./SaveIndicator.svelte";
    import type { SaveStatus } from "./SaveIndicator.svelte";
    import { createDebouncedSave, saveAnnotationState } from "$lib/utils/autosave.ts";
    import AnnotationEditor from "./AnnotationEditor.svelte";
    import type { EditorState } from "$lib/types.ts";

    interface Props {
        initialState: AnnotationState;
    }

    let { initialState }: Props = $props();

    let editorState = $state<EditorState>({ mode: 'closed' });

    let saveStatus = $state<SaveStatus>({ type: 'idle' });

    const { scheduleSave, cancelPending } = createDebouncedSave(2000);

    $effect(() => {
        const _entities = initialState.entities;
        const _pointers = initialState.pointers;
        const _relations = initialState.relations;
        const _completed = initialState.completed;

        saveStatus = { type: 'saving' };

        scheduleSave(initialState).then((result) => {
            if (result.success) {
                saveStatus = { type: 'saved', timestamp: new Date() };
            } else {
                saveStatus = { type: 'error', message: result.error || 'Unknown error' };
            }
        });
    });

    beforeNavigate(() => {
        cancelPending();
        saveAnnotationState(initialState);
    });

    function handleRetry() {
        saveStatus = { type: 'saving' };
        scheduleSave(initialState).then((result) => {
            if (result.success) {
                saveStatus = { type: 'saved', timestamp: new Date() };
            } else {
                saveStatus = { type: 'error', message: result.error || 'Unknown error' };
            }
        });
    }

    const body: string | undefined = initialState.reference.body;

    const validEntityIds = new globalThis.Set(initialState.entities.keys());
    const relationsArray = initialState.relations.toArray();
    const validRelations = relationsArray.filter(
        (relation) => validEntityIds.has(relation.subject) && validEntityIds.has(relation.object)
    );
    if (validRelations.length < relationsArray.length) {
        initialState.relations = Set(validRelations);
    }

    setContext("annotationState", initialState);
    setContext("editorState", {
        get value() { return editorState; },
        set value(s: EditorState) { editorState = s; },
    });
</script>

<div id="container">
    <div id="chunk">
        <ArticleBody {body} />
    </div>

    <div id="sidebar">
        <div id="summary">
            <Summary />
        </div>

        <div id="relations">
            <Relations />
        </div>
    </div>
</div>

<AnnotationEditor bind:editorState />

<SaveIndicator status={saveStatus} onRetry={handleRetry} />
