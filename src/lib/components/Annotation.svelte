<script lang="ts">
    import { setContext } from "svelte";
    import { SvelteMap, SvelteSet } from "svelte/reactivity";
    import { Set } from "immutable";
    import ChunkHeader from "$lib/components/ChunkHeader.svelte";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import { annotateHTMLString } from "$lib/annotation.svelte.ts";
    import type {
        AnnotationState,
        Entity,
        Relation,
        Pointer,
    } from "$lib/types.ts";
    import ArticleBody from "./ArticleBody.svelte";
    import SaveIndicator from "./SaveIndicator.svelte";
    import type { SaveStatus } from "./SaveIndicator.svelte";
    import { createDebouncedSave } from "$lib/utils/autosave.ts";

    interface Props {
        initialState: AnnotationState;
        apiUrl?: string;
    }

    let { initialState, apiUrl = "http://localhost:8000" }: Props = $props();

    let dropdownState = $state<{
        isOpen: boolean;
        position: { top: number; left: number };
        triggerElement: HTMLElement | null;
    }>({
        isOpen: false,
        position: { top: 0, left: 0 },
        triggerElement: null,
    });

    let saveStatus = $state<SaveStatus>({ type: 'idle' });

    const { scheduleSave, cancelPending } = createDebouncedSave(2000);

    // Watch for changes to annotation state and trigger auto-save
    $effect(() => {
        // Access reactive properties to trigger effect on changes
        const _entities = initialState.entities;
        const _pointers = initialState.pointers;
        const _relations = initialState.relations;

        // Trigger auto-save
        saveStatus = { type: 'saving' };

        scheduleSave(initialState, apiUrl).then((result) => {
            if (result.success) {
                saveStatus = { type: 'saved', timestamp: new Date() };
            } else {
                saveStatus = { type: 'error', message: result.error || 'Unknown error' };
            }
        });
    });

    function handleRetry() {
        saveStatus = { type: 'saving' };
        scheduleSave(initialState, apiUrl).then((result) => {
            if (result.success) {
                saveStatus = { type: 'saved', timestamp: new Date() };
            } else {
                saveStatus = { type: 'error', message: result.error || 'Unknown error' };
            }
        });
    }

    const body: string | undefined = initialState.reference.body;

    // Clean up any dangling relations (relations that reference non-existent entities)
    // This handles legacy data that may have dangling references from before the fix
    const validEntityIds = new Set(initialState.entities.keys());
    const relationsArray = initialState.relations.toArray();
    const validRelations = relationsArray.filter(
        (relation) => validEntityIds.has(relation.subject) && validEntityIds.has(relation.object)
    );
    if (validRelations.length < relationsArray.length) {
        initialState.relations = Set(validRelations);
    }

    setContext("annotationState", initialState);
    setContext("dropdownState", dropdownState);
</script>

<div id="container">
    <div id="chunk">
        <!-- <ChunkHeader /> -->
        <ArticleBody {body} />
    </div>

    <div id="summary">
        <Summary />
    </div>

    <div id="relations">
        <Relations />
    </div>
</div>

<SaveIndicator status={saveStatus} onRetry={handleRetry} />
