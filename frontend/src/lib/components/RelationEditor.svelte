<script lang="ts">
    import { getContext, onMount } from "svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import type { EditorState } from "$lib/types.ts";
    import { fetchProjectProperties } from "$lib/api.ts";
    import type { PropertyOption } from "$lib/api.ts";
    import { getLabelColor, getContrastColor } from "$lib/utils.ts";

    interface Props {
        editorState: EditorState;
    }

    let { editorState = $bindable() }: Props = $props();

    const annotationState = getContext<AnnotationState>("annotationState");

    let dialog: HTMLDialogElement;

    // ── Derived entities ─────────────────────────────────────────────────────

    const subjectEntity = $derived(
        editorState.mode === "create-relation"
            ? annotationState.entity(editorState.subjectEntityId)
            : null,
    );
    const objectEntity = $derived(
        editorState.mode === "create-relation"
            ? annotationState.entity(editorState.objectEntityId)
            : null,
    );

    // ── Property list ────────────────────────────────────────────────────────

    let allProperties = $state<PropertyOption[]>([]);
    onMount(() => {
        fetchProjectProperties(annotationState.project_id).then((props) => {
            allProperties = props;
        });
    });

    /** Properties sorted: recently used first, then alphabetically. */
    const sortedProperties = $derived.by(() => {
        const recent = annotationState.recentPredicates;
        return [...allProperties].sort((a, b) => {
            const ia = recent.indexOf(a.curie);
            const ib = recent.indexOf(b.curie);
            if (ia !== -1 && ib !== -1) return ia - ib;
            if (ia !== -1) return -1;
            if (ib !== -1) return 1;
            return a.label.localeCompare(b.label);
        });
    });

    // ── Selection ────────────────────────────────────────────────────────────

    let selectedCurie = $state<string | null>(null);

    // ── Dialog open/close ────────────────────────────────────────────────────

    $effect(() => {
        if (!dialog) return;
        if (editorState.mode === "create-relation") {
            selectedCurie = annotationState.recentPredicates[0] ?? null;
            dialog.showModal();
        } else {
            dialog.close();
        }
    });

    function close() {
        editorState = { mode: "closed" };
    }

    function confirm() {
        if (
            editorState.mode !== "create-relation" ||
            !selectedCurie
        ) return;
        annotationState.addRelation(
            editorState.subjectEntityId,
            selectedCurie,
            editorState.objectEntityId,
        );
        close();
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    function kindLabel(curie: string): string {
        return curie.includes(":") ? curie.split(":")[1] : curie;
    }
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<dialog
    bind:this={dialog}
    onclose={close}
    onkeydown={(e) => e.key === "Escape" && close()}
    class="relation-editor"
>
    {#if editorState.mode === "create-relation" && subjectEntity && objectEntity}
        <h2>New Relation</h2>

        <div class="entity-pair">
            <div
                class="entity-chip"
                style:background-color={getLabelColor(subjectEntity.kind)}
                style:color={getContrastColor(getLabelColor(subjectEntity.kind))}
            >
                <span class="entity-name">{subjectEntity.preferred_name}</span>
                <span class="entity-kind">{kindLabel(subjectEntity.kind)}</span>
            </div>

            <span class="arrow">→</span>

            <div
                class="entity-chip"
                style:background-color={getLabelColor(objectEntity.kind)}
                style:color={getContrastColor(getLabelColor(objectEntity.kind))}
            >
                <span class="entity-name">{objectEntity.preferred_name}</span>
                <span class="entity-kind">{kindLabel(objectEntity.kind)}</span>
            </div>
        </div>

        <p class="field-label">Property</p>

        {#if sortedProperties.length === 0}
            <p class="empty">No properties available for this project's ontologies.</p>
        {:else}
            <ul class="property-list">
                {#each sortedProperties as prop (prop.curie)}
                    {@const isRecent = annotationState.recentPredicates.includes(prop.curie)}
                    <li>
                        <label class="property-option">
                            <input
                                type="radio"
                                name="relation-property"
                                value={prop.curie}
                                bind:group={selectedCurie}
                            />
                            <span class="property-label">{prop.label}</span>
                            <span class="property-curie">{prop.curie}</span>
                            {#if prop.domain_curie || prop.range_curie}
                                <span class="property-signature">
                                    {prop.domain_curie ? kindLabel(prop.domain_curie) : "?"}
                                    →
                                    {prop.range_curie ? kindLabel(prop.range_curie) : "?"}
                                </span>
                            {/if}
                            {#if isRecent}
                                <span class="recent-badge">recent</span>
                            {/if}
                        </label>
                    </li>
                {/each}
            </ul>
        {/if}

        <div class="actions">
            <button
                class="btn-primary"
                onclick={confirm}
                disabled={!selectedCurie}
            >
                Confirm
            </button>
            <button class="btn-secondary" onclick={close}>Cancel</button>
        </div>
    {/if}
</dialog>

<style>
    .relation-editor {
        border: none;
        border-radius: 8px;
        padding: 1.5rem;
        width: min(480px, 90vw);
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }

    .relation-editor::backdrop {
        background: rgba(0, 0, 0, 0.4);
    }

    h2 {
        margin: 0 0 1.25rem;
        font-size: 1.1rem;
    }

    .entity-pair {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.25rem;
        flex-wrap: wrap;
    }

    .entity-chip {
        display: flex;
        flex-direction: column;
        padding: 0.4rem 0.75rem;
        border-radius: 6px;
        min-width: 0;
    }

    .entity-name {
        font-weight: 600;
        font-size: 0.9rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 160px;
    }

    .entity-kind {
        font-size: 0.7rem;
        opacity: 0.8;
        margin-top: 0.1rem;
    }

    .arrow {
        font-size: 1.25rem;
        color: #666;
        flex-shrink: 0;
    }

    .field-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #444;
        margin: 0 0 0.5rem;
    }

    .property-list {
        list-style: none;
        padding: 0;
        margin: 0 0 1.25rem;
        border: 1px solid #eee;
        border-radius: 6px;
        overflow: hidden;
        max-height: 260px;
        overflow-y: auto;
    }

    .property-list li + li {
        border-top: 1px solid #f0f0f0;
    }

    .property-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.55rem 0.75rem;
        cursor: pointer;
        font-size: 0.875rem;
    }

    .property-option:hover {
        background: #f5f5f5;
    }

    .property-label {
        font-weight: 500;
        flex: 1;
    }

    .property-curie {
        font-size: 0.75rem;
        color: #888;
        font-family: monospace;
    }

    .property-signature {
        font-size: 0.72rem;
        color: #999;
        border: 1px solid #e0e0e0;
        border-radius: 3px;
        padding: 0.05rem 0.3rem;
        white-space: nowrap;
    }

    .recent-badge {
        font-size: 0.68rem;
        font-weight: 600;
        color: #1a6b3a;
        background: #e6f5ec;
        border: 1px solid #a8d5b8;
        border-radius: 3px;
        padding: 0.05rem 0.3rem;
        white-space: nowrap;
    }

    .empty {
        font-size: 0.875rem;
        color: #888;
        margin: 0 0 1.25rem;
    }

    .actions {
        display: flex;
        gap: 0.5rem;
    }

    .btn-primary {
        padding: 0.5rem 1rem;
        background: #333;
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.875rem;
    }

    .btn-primary:hover:not(:disabled) { background: #111; }
    .btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

    .btn-secondary {
        padding: 0.5rem 1rem;
        background: #f0f0f0;
        color: #333;
        border: 1px solid #ccc;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.875rem;
    }

    .btn-secondary:hover { background: #e0e0e0; }
</style>
