<script lang="ts">
    import { browser } from "$app/environment";
    import { untrack } from "svelte";
    import type { PageData } from "./$types";
    import type { ClaimItem, EvidenceItem } from "./+page.server";
    import EntityBadge from "$lib/components/EntityBadge.svelte";
    import { getLabelColor, getContrastColor } from "$lib/colors.ts";
    import {
        type EvidenceParagraph,
        getParagraphRanges,
        buildEvidenceParagraphs,
    } from "$lib/evidence.ts";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();

    let activeTab = $state<"references" | "claims">("references");

    let evidenceReady = $state<Record<string, true>>({});
    const evidenceData: Record<
        string,
        Record<number, EvidenceParagraph[]>
    > = {};
    let expandedParas = $state<Record<string, true>>({});
    let expandedRefs = $state<Record<string, true>>({});
    let verdicts = $state<Record<number, "accepted" | "rejected" | null>>(
        untrack(() =>
            Object.fromEntries(
                data.claims.claims.map((c) => [c.relation_id, c.verdict]),
            ),
        ),
    );

    async function setVerdict(
        claim: ClaimItem,
        verdict: "accepted" | "rejected",
    ) {
        const prev = verdicts[claim.relation_id];
        verdicts[claim.relation_id] = verdict; // optimistic
        const res = await fetch(
            `/api/projects/${data.projectId}/curation/claims/${claim.relation_id}/verdict`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ verdict }),
            },
        );
        if (!res.ok) verdicts[claim.relation_id] = prev; // roll back on failure
    }

    function claimKey(claim: ClaimItem): string {
        return `${claim.subject}|${claim.predicate}|${claim.object}`;
    }

    function displayPredicate(predicate: string): string {
        const local = predicate.includes(":")
            ? predicate.slice(predicate.lastIndexOf(":") + 1)
            : predicate;
        return local
            .replace(/([A-Z])/g, " $1")
            .replace(/[-_]/g, " ")
            .toLowerCase()
            .trim();
    }

    // ---------------------------------------------------------------------------
    // Evidence paragraph extraction (browser-only)
    // ---------------------------------------------------------------------------

    function computeEvidenceSegments(
        ev: EvidenceItem,
        subjBg: string,
        objBg: string,
        subjFg: string,
        objFg: string,
    ): EvidenceParagraph[] {
        if (!ev.body) return [];
        const doc = new DOMParser().parseFromString(ev.body, "text/html");
        const plainText = doc.body.textContent ?? "";
        const paraRanges = getParagraphRanges(doc);
        return buildEvidenceParagraphs(
            plainText,
            paraRanges,
            ev.subject_pointers,
            ev.object_pointers,
            subjBg,
            objBg,
            subjFg,
            objFg,
        );
    }

    function handleEvidenceToggle(claim: ClaimItem, e: Event) {
        if (!(e.currentTarget as HTMLDetailsElement).open) return;
        const key = claimKey(claim);
        if (evidenceReady[key]) return;

        const subjBg = getLabelColor(
            data.claims.entities[claim.subject]?.kind ?? "",
        );
        const objBg = getLabelColor(
            data.claims.entities[claim.object]?.kind ?? "",
        );
        const subjFg = getContrastColor(subjBg);
        const objFg = getContrastColor(objBg);

        const byRef: Record<number, EvidenceParagraph[]> = {};
        for (const ev of claim.evidence) {
            byRef[ev.reference_id] = computeEvidenceSegments(
                ev,
                subjBg,
                objBg,
                subjFg,
                objFg,
            );
        }
        evidenceData[key] = byRef;
        evidenceReady[key] = true; // reactive trigger → re-render
    }

    const claimsByPredicate = $derived.by(() => {
        const map = new Map<string, ClaimItem[]>();
        for (const claim of data.claims.claims) {
            const bucket = map.get(claim.predicate);
            if (bucket) bucket.push(claim);
            else map.set(claim.predicate, [claim]);
        }
        return map;
    });
</script>

<div class="content-container">
    <h2>Curation Queue</h2>

    <div class="tab-bar">
        <button
            class="tab-btn"
            class:active={activeTab === "references"}
            onclick={() => (activeTab = "references")}
        >
            References
            {#if data.queue.length > 0}
                <span class="tab-count">{data.queue.length}</span>
            {/if}
        </button>
        <button
            class="tab-btn"
            class:active={activeTab === "claims"}
            onclick={() => (activeTab = "claims")}
        >
            Claims
            {#if data.claims.claims.length > 0}
                <span class="tab-count">{data.claims.claims.length}</span>
            {/if}
        </button>
    </div>

    {#if activeTab === "references"}
        {#if data.queue.length === 0}
            <p>No references are ready for curation yet.</p>
        {:else}
            <table class="table">
                <thead>
                    <tr>
                        <th>PubMed ID</th>
                        <th>Title</th>
                        <th>Authors</th>
                        <th>Year</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {#each data.queue as ref (ref.reference_id)}
                        <tr>
                            <td>{ref.pubmed_id ?? "—"}</td>
                            <td>{ref.title}</td>
                            <td>{ref.authors}</td>
                            <td>{ref.year}</td>
                            <td>
                                <a
                                    class="btn btn-sm primary"
                                    href="/curate/{ref.reference_id}?project={data.projectId}"
                                >
                                    Review
                                </a>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        {/if}
    {:else if data.claims.claims.length === 0}
        <p>No claims have been annotated yet.</p>
    {:else}
        <div class="claims-list">
            {#each claimsByPredicate.entries() as [predicate, claims] (predicate)}
                <div class="predicate-group">
                    <div class="predicate-label">
                        {displayPredicate(predicate)}
                    </div>
                    {#each claims as claim (claim.subject + claim.object)}
                        {@const subject = data.claims.entities[claim.subject]}
                        {@const object = data.claims.entities[claim.object]}
                        <div class="claim-row">
                            <div class="claim-triple">
                                {#if subject}
                                    <EntityBadge
                                        preferredName={subject.preferred_name}
                                        kind={subject.kind}
                                    />
                                {:else}
                                    <span class="unknown-entity"
                                        >{claim.subject}</span
                                    >
                                {/if}
                                <span class="arrow">→</span>
                                {#if object}
                                    <EntityBadge
                                        preferredName={object.preferred_name}
                                        kind={object.kind}
                                    />
                                {:else}
                                    <span class="unknown-entity"
                                        >{claim.object}</span
                                    >
                                {/if}
                            </div>
                            <div class="verdict-btns">
                                <button
                                    class="verdict-btn accept"
                                    class:active={verdicts[
                                        claim.relation_id
                                    ] === "accepted"}
                                    onclick={() =>
                                        setVerdict(claim, "accepted")}
                                    >Approve</button
                                >
                                <button
                                    class="verdict-btn reject"
                                    class:active={verdicts[
                                        claim.relation_id
                                    ] === "rejected"}
                                    onclick={() =>
                                        setVerdict(claim, "rejected")}
                                    >Reject</button
                                >
                            </div>
                            {#if claim.evidence.length > 0 && browser}
                                <details
                                    class="evidence-details"
                                    ontoggle={(e) =>
                                        handleEvidenceToggle(claim, e)}
                                >
                                    <summary>Show evidence</summary>
                                    <div class="evidence-body">
                                        {#each claim.evidence as ev (ev.reference_id)}
                                            {@const segs = evidenceReady[
                                                claimKey(claim)
                                            ]
                                                ? (evidenceData[
                                                      claimKey(claim)
                                                  ]?.[ev.reference_id] ?? [])
                                                : []}
                                            {@const refKey = `${claimKey(claim)}:${ev.reference_id}`}
                                            {@const visibleSegs = expandedRefs[
                                                refKey
                                            ]
                                                ? segs
                                                : segs.slice(0, 1)}
                                            <div class="evidence-ref">
                                                <div class="evidence-ref-title">
                                                    {ev.pubmed_id
                                                        ? `PMID:${ev.pubmed_id}`
                                                        : `Ref #${ev.reference_id}`}
                                                    — {ev.title}
                                                </div>
                                                {#each visibleSegs as seg, paraIdx (paraIdx)}
                                                    {@const paraKey = `${refKey}:${paraIdx}`}
                                                    <p
                                                        class="evidence-paragraph"
                                                    >
                                                        <!-- eslint-disable-next-line svelte/no-at-html-tags -->
                                                        {@html expandedParas[
                                                            paraKey
                                                        ] || !seg.isExcerpt
                                                            ? seg.fullHtml
                                                            : seg.excerptHtml}
                                                        {#if seg.isExcerpt && !expandedParas[paraKey]}
                                                            <button
                                                                class="expand-para-btn"
                                                                onclick={() => {
                                                                    expandedParas[
                                                                        paraKey
                                                                    ] = true;
                                                                }}
                                                                >(expand
                                                                paragraph)</button
                                                            >
                                                        {:else if seg.isExcerpt && expandedParas[paraKey]}
                                                            <button
                                                                class="expand-para-btn"
                                                                onclick={() => {
                                                                    delete expandedParas[
                                                                        paraKey
                                                                    ];
                                                                    expandedParas =
                                                                        expandedParas;
                                                                }}
                                                                >(collapse
                                                                paragraph)</button
                                                            >
                                                        {/if}
                                                    </p>
                                                {/each}
                                                {#if segs.length > 1 && !expandedRefs[refKey]}
                                                    <button
                                                        class="expand-para-btn"
                                                        onclick={() => {
                                                            expandedRefs[
                                                                refKey
                                                            ] = true;
                                                        }}
                                                        >(show {segs.length - 1} more
                                                        {segs.length - 1 === 1
                                                            ? "occurrence"
                                                            : "occurrences"})</button
                                                    >
                                                {/if}
                                                {#if evidenceReady[claimKey(claim)] && segs.length === 0}
                                                    <p
                                                        class="evidence-no-context"
                                                    >
                                                        No annotated spans found
                                                        for this reference.
                                                    </p>
                                                {/if}
                                            </div>
                                        {/each}
                                    </div>
                                </details>
                            {/if}
                        </div>
                    {/each}
                </div>
            {/each}
        </div>
    {/if}
</div>

<style>
    .tab-bar {
        display: flex;
        gap: 0.25rem;
        margin-bottom: 1.5rem;
        border-bottom: 2px solid #e5e7eb;
    }

    .tab-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.5rem 1rem;
        border: none;
        background: none;
        font-size: 1.4rem;
        color: #6b7280;
        cursor: pointer;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
        transition:
            color 0.15s,
            border-color 0.15s;
    }

    .tab-btn:hover {
        color: #374151;
    }

    .tab-btn.active {
        color: #111827;
        font-weight: 600;
        border-bottom-color: #374151;
    }

    .tab-count {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 1.25rem;
        height: 1.25rem;
        padding: 0 0.25rem;
        background-color: #e5e7eb;
        border-radius: 10px;
        font-size: 1.2rem;
        font-weight: 600;
        color: #374151;
    }

    .claims-list {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
    }

    .predicate-group {
        display: grid;
        grid-template-columns: max-content auto;
        align-items: start;
        row-gap: 0.5rem;
        column-gap: 0.75rem;
    }

    .predicate-label {
        grid-column: 1 / -1;
        font-size: 1.1rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
        padding-bottom: 0.25rem;
        border-bottom: 1px solid #e5e7eb;
    }

    .claim-row {
        display: contents;
    }

    .claim-triple {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        flex-wrap: wrap;
    }

    .arrow {
        color: #9ca3af;
        font-size: 1.4rem;
        flex-shrink: 0;
    }

    .verdict-btns {
        display: flex;
        flex-direction: row;
        gap: 0.35rem;
        align-self: center;
    }

    .verdict-btn {
        padding: 0.2rem 0.75rem;
        border-radius: 4px;
        font-size: 1.3rem;
        font-weight: 500;
        cursor: pointer;
        border: 1px solid transparent;
        transition:
            background-color 0.1s,
            color 0.1s;
    }

    .verdict-btn.accept {
        border-color: #16a34a;
        color: #16a34a;
        background: transparent;
    }

    .verdict-btn.accept:hover,
    .verdict-btn.accept.active {
        background: #16a34a;
        color: #fff;
    }

    .verdict-btn.reject {
        border-color: #dc2626;
        color: #dc2626;
        background: transparent;
    }

    .verdict-btn.reject:hover,
    .verdict-btn.reject.active {
        background: #dc2626;
        color: #fff;
    }

    .unknown-entity {
        font-family: monospace;
        font-size: 1.3rem;
        color: #6b7280;
        background: #f3f4f6;
        padding: 0.2rem 0.4rem;
        border-radius: 3px;
    }

    .evidence-details {
        grid-column: 1 / -1;
        contain: inline-size;
        margin-left: 0.25rem;
    }

    .evidence-details summary {
        font-size: 1.3rem;
        color: #6b7280;
        cursor: pointer;
        user-select: none;
        width: fit-content;
    }

    .evidence-details summary:hover {
        color: #374151;
    }

    .evidence-body {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-top: 0.5rem;
        padding-left: 0.75rem;
        border-left: 2px solid #e5e7eb;
    }

    .evidence-ref-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.25rem;
    }

    .evidence-paragraph {
        font-size: 1.4rem;
        line-height: 1.6;
        margin: 0.25rem 0;
        color: #374151;
    }

    .evidence-no-context {
        font-size: 1.2rem;
        color: #9ca3af;
        font-style: italic;
        margin: 0;
    }

    .expand-para-btn {
        display: inline;
        border: none;
        background: none;
        padding: 0 0.2rem;
        font-size: 1.3rem;
        color: #6b7280;
        cursor: pointer;
        font-style: italic;
    }

    .expand-para-btn:hover {
        color: #374151;
        text-decoration: underline;
    }
</style>
