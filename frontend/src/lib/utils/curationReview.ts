/**
 * Pure derivation of the curation-review view model from a reference's
 * annotator snapshots and any previously-saved curated annotation.
 *
 * Kept free of DOM / Svelte so it can be recomputed reactively (via
 * `$derived.by`) whenever the loaded page data changes — e.g. after a curator
 * renames a proposed entity's CURIE and the page re-fetches — and unit-tested
 * in isolation.
 */

export interface ReviewEntity {
    entity_id: string;
    preferred_name: string;
    kind: string;
    confirmed: boolean;
}

export interface ReviewPointer {
    reference_id: number;
    entity_id: string;
    offset: number;
    length: number;
    field: string;
    exact_text: string;
    prefix_text: string;
    suffix_text: string;
}

export interface ReviewRelation {
    relation_id: number | null;
    predicate: string;
    subject: string;
    object: string;
}

export interface ReviewSnapshot {
    user_id: string;
    email: string;
    reference_id: number;
    pointers: ReviewPointer[];
    relations: ReviewRelation[];
    created_at: string;
}

export interface ReviewInput {
    entities: Record<string, ReviewEntity>;
    snapshots: ReviewSnapshot[];
    curated_pointers: ReviewPointer[];
    curated_relations: ReviewRelation[];
}

export type PointerKey = string;
export type RelationKey = string;

export interface SpanEntry {
    key: PointerKey;
    p: ReviewPointer;
}

export function pointerKey(p: ReviewPointer): PointerKey {
    return `${p.entity_id}|${p.field}|${p.offset}|${p.length}`;
}

export function relationKey(r: ReviewRelation): RelationKey {
    return `${r.predicate}|${r.subject}|${r.object}`;
}

export interface ReviewModel {
    pointerAnnotators: Map<PointerKey, Set<string>>;
    pointerData: Map<PointerKey, ReviewPointer>;
    entityAnnotators: Map<string, Set<string>>;
    relationAnnotators: Map<RelationKey, Set<string>>;
    relationData: Map<RelationKey, ReviewRelation>;
    abstractSpansByOffset: SpanEntry[];
    bodySpansByOffset: SpanEntry[];
    spanIndexByKey: Map<PointerKey, number>;
    acceptedPointerKeys: Set<PointerKey>;
    acceptedRelationKeys: Set<RelationKey>;
    acceptedEntityIds: Set<string>;
    sortedPointerKeys: PointerKey[];
    pointerKeysByEntity: Map<string, PointerKey[]>;
    sortedEntityIds: string[];
    sortedRelationKeys: RelationKey[];
    hasSavedCuration: boolean;
}

export function computeReviewModel(input: ReviewInput): ReviewModel {
    const { entities, snapshots, curated_pointers, curated_relations } = input;

    const pointerAnnotators = new Map<PointerKey, Set<string>>();
    const pointerData = new Map<PointerKey, ReviewPointer>();
    for (const snap of snapshots) {
        for (const p of snap.pointers) {
            const k = pointerKey(p);
            if (!pointerAnnotators.has(k)) {
                pointerAnnotators.set(k, new Set());
                pointerData.set(k, p);
            }
            pointerAnnotators.get(k)!.add(snap.email);
        }
    }

    const entityAnnotators = new Map<string, Set<string>>();
    for (const snap of snapshots) {
        for (const p of snap.pointers) {
            if (!entityAnnotators.has(p.entity_id)) {
                entityAnnotators.set(p.entity_id, new Set());
            }
            entityAnnotators.get(p.entity_id)!.add(snap.email);
        }
    }

    const relationAnnotators = new Map<RelationKey, Set<string>>();
    const relationData = new Map<RelationKey, ReviewRelation>();
    for (const snap of snapshots) {
        for (const r of snap.relations) {
            const k = relationKey(r);
            if (!relationAnnotators.has(k)) {
                relationAnnotators.set(k, new Set());
                relationData.set(k, r);
            }
            relationAnnotators.get(k)!.add(snap.email);
        }
    }

    const abstractSpansByOffset: SpanEntry[] = [...pointerAnnotators.keys()]
        .filter((k) => pointerData.get(k)!.field === "abstract")
        .map((k) => ({ key: k, p: pointerData.get(k)! }))
        .sort((a, b) => a.p.offset - b.p.offset || b.p.length - a.p.length);

    const bodySpansByOffset: SpanEntry[] = [...pointerAnnotators.keys()]
        .filter((k) => pointerData.get(k)!.field !== "abstract")
        .map((k) => ({ key: k, p: pointerData.get(k)! }))
        .sort((a, b) => a.p.offset - b.p.offset || b.p.length - a.p.length);

    const spansByOffset: SpanEntry[] = [
        ...abstractSpansByOffset,
        ...bodySpansByOffset,
    ];
    const spanIndexByKey = new Map(spansByOffset.map((s, i) => [s.key, i]));

    const acceptedPointerKeys = new Set<PointerKey>(
        curated_pointers.map((p) => pointerKey(p)),
    );
    const acceptedRelationKeys = new Set<RelationKey>(
        curated_relations.map((r) => relationKey(r)),
    );
    const acceptedEntityIds = new Set<string>(
        curated_pointers.map((p) => p.entity_id),
    );

    const sortedPointerKeys = [...pointerAnnotators.keys()].sort((a, b) => {
        const aAccepted = acceptedPointerKeys.has(a) ? 1 : 0;
        const bAccepted = acceptedPointerKeys.has(b) ? 1 : 0;
        if (aAccepted !== bAccepted) return aAccepted - bAccepted;
        const countDiff =
            pointerAnnotators.get(b)!.size - pointerAnnotators.get(a)!.size;
        if (countDiff !== 0) return countDiff;
        const nameA =
            entities[pointerData.get(a)!.entity_id]?.preferred_name ?? a;
        const nameB =
            entities[pointerData.get(b)!.entity_id]?.preferred_name ?? b;
        return nameA.localeCompare(nameB);
    });

    const pointerKeysByEntity = new Map<string, PointerKey[]>();
    for (const k of sortedPointerKeys) {
        const eid = pointerData.get(k)!.entity_id;
        const list = pointerKeysByEntity.get(eid);
        if (list) list.push(k);
        else pointerKeysByEntity.set(eid, [k]);
    }

    const sortedEntityIds = [...entityAnnotators.keys()].sort((a, b) => {
        const aAccepted = acceptedEntityIds.has(a) ? 1 : 0;
        const bAccepted = acceptedEntityIds.has(b) ? 1 : 0;
        if (aAccepted !== bAccepted) return aAccepted - bAccepted;
        const countDiff =
            entityAnnotators.get(b)!.size - entityAnnotators.get(a)!.size;
        if (countDiff !== 0) return countDiff;
        return (entities[a]?.preferred_name ?? a).localeCompare(
            entities[b]?.preferred_name ?? b,
        );
    });

    const sortedRelationKeys = [...relationAnnotators.keys()].sort((a, b) => {
        const aAccepted = acceptedRelationKeys.has(a) ? 1 : 0;
        const bAccepted = acceptedRelationKeys.has(b) ? 1 : 0;
        if (aAccepted !== bAccepted) return aAccepted - bAccepted;
        return (
            relationAnnotators.get(b)!.size - relationAnnotators.get(a)!.size
        );
    });

    const hasSavedCuration =
        acceptedPointerKeys.size > 0 || acceptedRelationKeys.size > 0;

    return {
        pointerAnnotators,
        pointerData,
        entityAnnotators,
        relationAnnotators,
        relationData,
        abstractSpansByOffset,
        bodySpansByOffset,
        spanIndexByKey,
        acceptedPointerKeys,
        acceptedRelationKeys,
        acceptedEntityIds,
        sortedPointerKeys,
        pointerKeysByEntity,
        sortedEntityIds,
        sortedRelationKeys,
        hasSavedCuration,
    };
}
