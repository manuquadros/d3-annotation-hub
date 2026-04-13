<script lang="ts">
    import { getContext, onMount } from "svelte";
    import { AnnotationState } from "$lib/annotation.svelte";
    import type { EditorState } from "$lib/types.ts";
    import { fetchProjectProperties, fetchEntityTypes } from "$lib/api.ts";
    import type { PropertyOption, KindOption } from "$lib/api.ts";
    import { getLabelColor, getContrastColor } from "$lib/utils.ts";

    interface Props {
        editorState: EditorState;
    }

    let { editorState = $bindable() }: Props = $props();

    const annotationState = getContext<AnnotationState>("annotationState");

    let dialog: HTMLDialogElement;
    let searchInput: HTMLInputElement;

    // ── Remote data ──────────────────────────────────────────────────────────

    let allProperties = $state<PropertyOption[]>([]);
    let entityTypes = $state<KindOption[]>([]);

    onMount(() => {
        fetchProjectProperties(annotationState.project_id).then((p) => (allProperties = p));
        fetchEntityTypes().then((k) => (entityTypes = k));
    });

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

    // ── View state ───────────────────────────────────────────────────────────

    type View = "select" | "propose";
    let view = $state<View>("select");

    // ── Search & property lists ──────────────────────────────────────────────

    let query = $state("");

    const MAX_RECENT = 10;

    const recentProperties = $derived.by(() => {
        const recent = annotationState.recentPredicates.slice(0, MAX_RECENT);
        return recent
            .map((curie) => allProperties.find((p) => p.curie === curie))
            .filter((p): p is PropertyOption => p !== undefined);
    });

    const filteredProperties = $derived.by(() => {
        const q = query.trim().toLowerCase();
        if (!q) return allProperties;
        return allProperties.filter(
            (p) =>
                p.label.toLowerCase().includes(q) ||
                p.curie.toLowerCase().includes(q),
        );
    });

    /** Non-recent properties for the "All" section (only when search is empty). */
    const remainingProperties = $derived.by(() => {
        const recentCuries = new Set(recentProperties.map((p) => p.curie));
        return [...allProperties]
            .filter((p) => !recentCuries.has(p.curie))
            .sort((a, b) => a.label.localeCompare(b.label));
    });

    // ── Selection ────────────────────────────────────────────────────────────

    let selectedCurie = $state<string | null>(null);

    // ── Dialog lifecycle ─────────────────────────────────────────────────────

    $effect(() => {
        if (!dialog) return;
        if (editorState.mode === "create-relation") {
            selectedCurie = annotationState.recentPredicates[0] ?? null;
            query = "";
            view = "select";
            dialog.showModal();
            // Focus search once the DOM settles
            requestAnimationFrame(() => searchInput?.focus());
        } else {
            dialog.close();
        }
    });

    function close() {
        editorState = { mode: "closed" };
    }

    function confirm() {
        if (editorState.mode !== "create-relation" || !selectedCurie) return;
        annotationState.addRelation(
            editorState.subjectEntityId,
            selectedCurie,
            editorState.objectEntityId,
        );
        close();
    }

    // ── Propose form state ───────────────────────────────────────────────────

    let proposedLabel = $state("");
    let proposedCurie = $state("");
    let proposedDomain = $state("");
    let proposedRange = $state("");

    function openPropose() {
        proposedLabel = query.trim(); // pre-fill with whatever they typed
        proposedCurie = "";
        proposedDomain = "";
        proposedRange = "";
        view = "propose";
    }

    function backToSelect() {
        view = "select";
        requestAnimationFrame(() => searchInput?.focus());
    }

    function submitProposal() {
        const label = proposedLabel.trim();
        if (!label) return;

        const curie =
            proposedCurie.trim() ||
            `proposed:${label.toLowerCase().replace(/\s+/g, "-")}`;

        const newProp: PropertyOption = {
            curie,
            label,
            domain_curie: proposedDomain || null,
            range_curie: proposedRange || null,
        };

        // Add to the session property list if not already present
        if (!allProperties.some((p) => p.curie === curie)) {
            allProperties = [...allProperties, newProp];
        }

        selectedCurie = curie;
        view = "select";
        query = "";
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

        {#if view === "select"}
            <!-- ── Search ──────────────────────────────────────────────── -->
            <div class="search-row">
                <i class="ph ph-magnifying-glass search-icon"></i>
                <input
                    bind:this={searchInput}
                    bind:value={query}
                    type="search"
                    class="search-input"
                    placeholder="Search properties…"
                />
            </div>

            <!-- ── Property list ──────────────────────────────────────── -->
            {#if allProperties.length === 0}
                <p class="empty">No properties available for this project's ontologies.</p>
            {:else if query.trim()}
                <!-- Filtered results -->
                {#if filteredProperties.length === 0}
                    <div class="no-results">
                        <p>No properties matching <strong>"{query}"</strong>.</p>
                        <button class="propose-link" onclick={openPropose}>
                            <i class="ph ph-plus-circle"></i>
                            Propose "{query}" as a new property
                        </button>
                    </div>
                {:else}
                    <ul class="property-list">
                        {#each filteredProperties as prop (prop.curie)}
                            {@const isRecent = annotationState.recentPredicates.includes(prop.curie)}
                            <li>
                                <label class="property-option">
                                    <input type="radio" name="relation-property" value={prop.curie} bind:group={selectedCurie} />
                                    <span class="property-label">{prop.label}</span>
                                    <span class="property-curie">{prop.curie}</span>
                                    {#if prop.domain_curie || prop.range_curie}
                                        <span class="property-signature">
                                            {prop.domain_curie ? kindLabel(prop.domain_curie) : "?"}
                                            →
                                            {prop.range_curie ? kindLabel(prop.range_curie) : "?"}
                                        </span>
                                    {/if}
                                    {#if isRecent}<span class="recent-badge">recent</span>{/if}
                                </label>
                            </li>
                        {/each}
                    </ul>
                {/if}
            {:else}
                <!-- Unfiltered: recent + remaining -->
                <ul class="property-list">
                    {#if recentProperties.length > 0}
                        <li class="list-section-label">Recently used</li>
                        {#each recentProperties as prop (prop.curie)}
                            <li>
                                <label class="property-option">
                                    <input type="radio" name="relation-property" value={prop.curie} bind:group={selectedCurie} />
                                    <span class="property-label">{prop.label}</span>
                                    <span class="property-curie">{prop.curie}</span>
                                    {#if prop.domain_curie || prop.range_curie}
                                        <span class="property-signature">
                                            {prop.domain_curie ? kindLabel(prop.domain_curie) : "?"}
                                            →
                                            {prop.range_curie ? kindLabel(prop.range_curie) : "?"}
                                        </span>
                                    {/if}
                                    <span class="recent-badge">recent</span>
                                </label>
                            </li>
                        {/each}
                    {/if}
                    {#if remainingProperties.length > 0}
                        {#if recentProperties.length > 0}
                            <li class="list-section-label">All properties</li>
                        {/if}
                        {#each remainingProperties as prop (prop.curie)}
                            <li>
                                <label class="property-option">
                                    <input type="radio" name="relation-property" value={prop.curie} bind:group={selectedCurie} />
                                    <span class="property-label">{prop.label}</span>
                                    <span class="property-curie">{prop.curie}</span>
                                    {#if prop.domain_curie || prop.range_curie}
                                        <span class="property-signature">
                                            {prop.domain_curie ? kindLabel(prop.domain_curie) : "?"}
                                            →
                                            {prop.range_curie ? kindLabel(prop.range_curie) : "?"}
                                        </span>
                                    {/if}
                                </label>
                            </li>
                        {/each}
                    {/if}
                </ul>
            {/if}

            <!-- Always-available propose link -->
            {#if query.trim() === "" || filteredProperties.length > 0}
                <button class="propose-link propose-link--subtle" onclick={openPropose}>
                    <i class="ph ph-plus-circle"></i>
                    Propose a new property
                </button>
            {/if}

            <div class="actions">
                <button class="btn-primary" onclick={confirm} disabled={!selectedCurie}>Confirm</button>
                <button class="btn-secondary" onclick={close}>Cancel</button>
            </div>

        {:else}
            <!-- ── Propose form ─────────────────────────────────────── -->
            <button class="back-link" onclick={backToSelect}>
                <i class="ph ph-arrow-left"></i> Back to search
            </button>

            <p class="field-label">New property</p>

            <div class="propose-form">
                <div class="form-field">
                    <label for="prop-label">Label <span class="required">*</span></label>
                    <input
                        id="prop-label"
                        type="text"
                        bind:value={proposedLabel}
                        placeholder="e.g. isolated from"
                        required
                    />
                </div>

                <div class="form-field">
                    <label for="prop-curie">
                        CURIE
                        <span class="optional">(optional — auto-generated if blank)</span>
                    </label>
                    <input
                        id="prop-curie"
                        type="text"
                        bind:value={proposedCurie}
                        placeholder="e.g. RO:0001025"
                    />
                </div>

                <div class="form-row">
                    <div class="form-field">
                        <label for="prop-domain">Domain <span class="optional">(optional)</span></label>
                        <select id="prop-domain" bind:value={proposedDomain}>
                            <option value="">Any</option>
                            {#each entityTypes as k (k.curie)}
                                <option value={k.curie}>{k.label}</option>
                            {/each}
                        </select>
                    </div>
                    <div class="form-field">
                        <label for="prop-range">Range <span class="optional">(optional)</span></label>
                        <select id="prop-range" bind:value={proposedRange}>
                            <option value="">Any</option>
                            {#each entityTypes as k (k.curie)}
                                <option value={k.curie}>{k.label}</option>
                            {/each}
                        </select>
                    </div>
                </div>

                <button
                    class="btn-primary"
                    onclick={submitProposal}
                    disabled={!proposedLabel.trim()}
                >
                    Create and use
                </button>
            </div>
        {/if}
    {/if}
</dialog>

<style>
    .relation-editor {
        border: none;
        border-radius: 8px;
        padding: 1.5rem;
        width: min(520px, 92vw);
        max-height: 85vh;
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

    /* ── Entity pair ── */

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

    /* ── Search ── */

    .search-row {
        position: relative;
        margin-bottom: 0.5rem;
    }

    .search-icon {
        position: absolute;
        left: 0.6rem;
        top: 50%;
        transform: translateY(-50%);
        color: #999;
        font-size: 0.9rem;
        pointer-events: none;
    }

    .search-input {
        width: 100%;
        padding: 0.45rem 0.5rem 0.45rem 2rem;
        border: 1px solid #d0d0d0;
        border-radius: 5px;
        font-size: 0.875rem;
        box-sizing: border-box;
        outline: none;
    }

    .search-input:focus {
        border-color: #888;
    }

    /* ── Property list ── */

    .property-list {
        list-style: none;
        padding: 0;
        margin: 0 0 0.5rem;
        border: 1px solid #eee;
        border-radius: 6px;
        overflow: hidden;
        max-height: 280px;
        overflow-y: auto;
    }

    .list-section-label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #999;
        padding: 0.4rem 0.75rem 0.25rem;
        background: #fafafa;
        border-bottom: 1px solid #f0f0f0;
    }

    .property-list li + li {
        border-top: 1px solid #f0f0f0;
    }

    .list-section-label + li {
        border-top: none;
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

    /* ── No results ── */

    .no-results {
        padding: 0.75rem 0;
        margin-bottom: 0.5rem;
    }

    .no-results p {
        font-size: 0.875rem;
        color: #666;
        margin: 0 0 0.5rem;
    }

    /* ── Propose link ── */

    .propose-link {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: none;
        border: 1px solid #c0d0e8;
        border-radius: 5px;
        padding: 0.35rem 0.65rem;
        color: #2a5ba0;
        font-size: 0.82rem;
        cursor: pointer;
        margin-bottom: 1rem;
    }

    .propose-link:hover {
        background: #edf3fc;
    }

    .propose-link--subtle {
        color: #777;
        border-color: #ddd;
        font-size: 0.8rem;
    }

    .propose-link--subtle:hover {
        background: #f5f5f5;
        color: #333;
    }

    /* ── Back link ── */

    .back-link {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: none;
        border: none;
        color: #555;
        font-size: 0.83rem;
        cursor: pointer;
        padding: 0;
        margin-bottom: 1rem;
    }

    .back-link:hover {
        color: #111;
    }

    /* ── Propose form ── */

    .propose-form {
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
        margin-bottom: 1rem;
    }

    .form-row {
        display: flex;
        gap: 0.75rem;
    }

    .form-field {
        display: flex;
        flex-direction: column;
        gap: 0.3rem;
        flex: 1;
    }

    .form-field label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #444;
    }

    .form-field input[type="text"],
    .form-field select {
        padding: 0.4rem 0.5rem;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 0.875rem;
        width: 100%;
        box-sizing: border-box;
    }

    .form-field input[type="text"]:focus,
    .form-field select:focus {
        border-color: #888;
        outline: none;
    }

    .field-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: #444;
        margin: 0 0 0.6rem;
    }

    .required {
        color: #c00;
        font-weight: 400;
    }

    .optional {
        font-weight: 400;
        text-transform: none;
        letter-spacing: 0;
        color: #888;
        font-size: 0.72rem;
    }

    .empty {
        font-size: 0.875rem;
        color: #888;
        margin: 0 0 1.25rem;
    }

    /* ── Actions ── */

    .actions {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
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
