<script lang="ts">
    import { setContext } from "svelte";
    import { SvelteMap, SvelteSet } from "svelte/reactivity";
    import ChunkHeader from "$lib/components/ChunkHeader.svelte";
    import Summary from "$lib/components/Summary.svelte";
    import Relations from "$lib/components/Relations.svelte";
    import { annotateHTMLString } from "$lib/annotation.ts";
    import type {
        AnnotationState,
        Entity,
        Relation,
        Pointer,
    } from "$lib/types.ts";
    import ArticleBody from "./ArticleBody.svelte";

    interface Props {
        initialState: AnnotationState;
    }

    let { initialState }: Props = $props();

    let entities: SvelteMap<string, Entity> | null = $state(
        new SvelteMap(initialState.entities),
    );
    let pointers: SvelteMap<number, Pointer> = $state(
        new SvelteMap(initialState.pointers),
    );
    let relations: SvelteSet<Relation> = $state(
        new SvelteSet(initialState.relations),
    );

    let dropdownState = $state<{
        isOpen: boolean;
        position: { top: number; left: number };
        triggerElement: HTMLElement | null;
    }>({
        isOpen: false,
        position: { top: 0, left: 0 },
        triggerElement: null,
    });

    const body: string | undefined = initialState.reference.body;

    setContext("entities", entities);
    setContext("pointers", pointers);
    setContext("relations", relations);
    setContext("dropdownState", dropdownState);
</script>

<div id="container">
    <div id="chunk">
        <!-- <ChunkHeader /> -->
        <ArticleBody {body} />
    </div>

    <!-- <div id="summary"> -->
    <!--     <Summary /> -->
    <!-- </div> -->

    <!-- <div id="relations"> -->
    <!--     <Relations /> -->
    <!-- </div> -->
</div>
