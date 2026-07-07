import type { Relation, Pointer, User, Reference, Entity } from "$lib/types.ts";
import { AnnotationStateSchema, createRelation } from "$lib/types.ts";
import { mount, unmount } from "svelte";
import { Map, Set } from "immutable";
import type { Map as ImmutableMap, Set as ImmutableSet } from "immutable";
import DOMPurify from "dompurify";
import ResourceCard from "$lib/components/ResourceCard.svelte";

interface AnnotatedRange {
    range: Range | null;
    pointer_id: string;
    label: string;
}

interface Snapshot {
    entities: ImmutableMap<string, Entity>;
    pointers: ImmutableMap<string, Pointer>;
    relations: ImmutableSet<Relation>;
}

const CONTEXT_SIZE = 32;

function buildTextQuoteSelector(
    plainText: string,
    offset: number,
    length: number,
): { exact_text: string; prefix_text: string; suffix_text: string } {
    return {
        exact_text: plainText.slice(offset, offset + length),
        prefix_text: plainText.slice(
            Math.max(0, offset - CONTEXT_SIZE),
            offset,
        ),
        suffix_text: plainText.slice(
            offset + length,
            offset + length + CONTEXT_SIZE,
        ),
    };
}

function commonPrefixLength(a: string, b: string): number {
    let i = 0;
    while (i < a.length && i < b.length && a[i] === b[i]) i++;
    return i;
}

function commonSuffixLength(a: string, b: string): number {
    let i = a.length - 1,
        j = b.length - 1,
        count = 0;
    while (i >= 0 && j >= 0 && a[i] === b[j]) {
        i--;
        j--;
        count++;
    }
    return count;
}

/**
 * Resolves the actual offset of a pointer in the given plain text using the
 * stored TextQuoteSelector. Tries the stored offset first (fast path); falls
 * back to a full-text search disambiguated by prefix/suffix context.
 */
export function resolvePointerOffset(
    pointer: Pointer,
    plainText: string,
): { offset: number; length: number } | null {
    if (!pointer.exact_text) {
        // No TQS data — trust the raw offset if it's in range.
        if (pointer.offset + pointer.length <= plainText.length) {
            return { offset: pointer.offset, length: pointer.length };
        }
        return null;
    }

    // Fast path: stored offset still points to the right text.
    if (
        plainText.slice(pointer.offset, pointer.offset + pointer.length) ===
        pointer.exact_text
    ) {
        return { offset: pointer.offset, length: pointer.length };
    }

    // Fallback: search for all occurrences of exact_text.
    const occurrences = allOccurrences(plainText, pointer.exact_text);
    if (occurrences.length === 0) return null;
    if (occurrences.length === 1) {
        return {
            offset: occurrences[0].offset,
            length: pointer.exact_text.length,
        };
    }

    // Disambiguate by prefix/suffix overlap score.
    let bestScore = -1;
    let best: { offset: number; length: number } | null = null;
    for (const { offset } of occurrences) {
        const length = pointer.exact_text.length;
        const actualPrefix = plainText.slice(
            Math.max(0, offset - CONTEXT_SIZE),
            offset,
        );
        const actualSuffix = plainText.slice(
            offset + length,
            offset + length + CONTEXT_SIZE,
        );
        const score =
            commonSuffixLength(pointer.prefix_text, actualPrefix) +
            commonPrefixLength(pointer.suffix_text, actualSuffix);
        if (score > bestScore) {
            bestScore = score;
            best = { offset, length };
        }
    }
    return best;
}

export class AnnotationState {
    user: User;
    reference: Reference;
    project_id!: number;
    entities: ImmutableMap<string, Entity> = $state(Map());
    pointers: ImmutableMap<string, Pointer> = $state(Map());
    relations: ImmutableSet<Relation> = $state(Set());
    completed: boolean = $state(false);
    /** Predicates used in this session, most recent first (not persisted). */
    recentPredicates: string[] = $state([]);

    #past: Snapshot[] = $state([]);
    #future: Snapshot[] = $state([]);
    #pointerCounter: number = 0;

    canUndo = $derived(this.#past.length > 0);
    canRedo = $derived(this.#future.length > 0);

    constructor(annotationData: string | object) {
        const parsed =
            typeof annotationData === "string"
                ? JSON.parse(annotationData)
                : annotationData;
        const validated = AnnotationStateSchema.parse(parsed);
        this.user = validated.user;
        this.reference = validated.reference;
        this.project_id = validated.project_id;
        this.entities = validated.entities;
        this.pointers = validated.pointers;
        this.relations = validated.relations;
        this.completed = validated.completed;
        this.#pointerCounter =
            this.pointers
                .keySeq()
                .map((k) => parseInt(k.slice(4), 10))
                .filter((n) => !isNaN(n))
                .max() ?? 0;
    }

    #nextPointerKey(): string {
        return `ptr_${++this.#pointerCounter}`;
    }

    #snapshot(): Snapshot {
        return {
            entities: this.entities,
            pointers: this.pointers,
            relations: this.relations,
        };
    }

    #commit(snapshot: Snapshot): void {
        this.#past = [...this.#past, snapshot];
        this.#future = [];
    }

    undo(): void {
        if (this.#past.length === 0) return;
        const prev = this.#past[this.#past.length - 1];
        this.#future = [this.#snapshot(), ...this.#future];
        this.#past = this.#past.slice(0, -1);
        this.entities = prev.entities;
        this.pointers = prev.pointers;
        this.relations = prev.relations;
    }

    redo(): void {
        if (this.#future.length === 0) return;
        const next = this.#future[0];
        this.#past = [...this.#past, this.#snapshot()];
        this.#future = this.#future.slice(1);
        this.entities = next.entities;
        this.pointers = next.pointers;
        this.relations = next.relations;
    }

    markComplete(): void {
        this.completed = true;
    }

    markIncomplete(): void {
        this.completed = false;
    }

    #getPlainText(field: "abstract" | "body"): string {
        const html =
            field === "abstract"
                ? this.reference.abstract
                : this.reference.body;
        if (!html) return "";
        const tempDiv = globalThis.document?.createElement("div");
        if (!tempDiv) return "";
        tempDiv.innerHTML = DOMPurify.sanitize(html);
        return tempDiv.textContent || "";
    }

    /**
     * Creates a new entity with the given kind and preferred name, then creates
     * pointers at each offset within the given field. The text at each offset is
     * added as a synonym. Propagates the annotation to all other identical
     * uncovered occurrences within the same field.
     */
    add(
        kind: string,
        preferredName: string,
        offsets: Array<{ offset: number; length: number }>,
        field: "abstract" | "body",
    ): void {
        const before = this.#snapshot();
        const plainText = this.#getPlainText(field);
        const synonyms = new globalThis.Set<string>();

        const trimmedName = preferredName.trim();
        if (trimmedName) synonyms.add(trimmedName);

        for (const { offset, length } of offsets) {
            const text = plainText.slice(offset, offset + length).trim();
            if (text) synonyms.add(text);
        }

        const newEntityId = this.#createEntity(kind, preferredName, synonyms);

        let updatedPointers = this.pointers;
        for (const { offset, length } of offsets) {
            const key = this.#nextPointerKey();
            updatedPointers = updatedPointers.set(key, {
                entity_id: newEntityId,
                reference_id: this.reference.reference_id,
                offset,
                length,
                field,
                ...buildTextQuoteSelector(plainText, offset, length),
            });
        }
        this.pointers = updatedPointers;

        // Propagate to all other identical uncovered occurrences in the same field.
        const searchText = offsets[0]
            ? plainText.slice(
                  offsets[0].offset,
                  offsets[0].offset + offsets[0].length,
              )
            : "";
        if (searchText) {
            const candidates = allOccurrences(plainText, searchText);
            const fieldPointers = this.pointers.filter(
                (p) => p.field === field,
            );
            const extras = uncoveredOffsets(candidates, fieldPointers);
            let propagated = this.pointers;
            for (const { offset, length } of extras) {
                const key = this.#nextPointerKey();
                propagated = propagated.set(key, {
                    entity_id: newEntityId,
                    reference_id: this.reference.reference_id,
                    offset,
                    length,
                    field,
                    ...buildTextQuoteSelector(plainText, offset, length),
                });
            }
            this.pointers = propagated;
        }

        this.#commit(before);
    }

    /**
     * Adds new pointer(s) to an existing entity and appends the highlighted
     * text as a synonym if it isn't already present. Propagates the annotation
     * to all other identical uncovered occurrences within the same field.
     */
    addToExistingEntity(
        entityId: string,
        synonym: string,
        offsets: Array<{ offset: number; length: number }>,
        field: "abstract" | "body",
    ): void {
        const before = this.#snapshot();
        const entity = this.entities.get(entityId);
        if (!entity) return;

        const trimmed = synonym.trim();
        if (trimmed && !entity.synonyms.has(trimmed)) {
            this.entities = this.entities.set(entityId, {
                ...entity,
                synonyms: entity.synonyms.add(trimmed),
            });
        }

        const plainText = this.#getPlainText(field);

        let updatedPointers = this.pointers;
        for (const { offset, length } of offsets) {
            const key = this.#nextPointerKey();
            updatedPointers = updatedPointers.set(key, {
                entity_id: entityId,
                reference_id: this.reference.reference_id,
                offset,
                length,
                field,
                ...buildTextQuoteSelector(plainText, offset, length),
            });
        }
        this.pointers = updatedPointers;

        // Propagate to all other identical uncovered occurrences in the same field.
        const searchText = trimmed;
        if (searchText) {
            const candidates = allOccurrences(plainText, searchText);
            const fieldPointers = this.pointers.filter(
                (p) => p.field === field,
            );
            const extras = uncoveredOffsets(candidates, fieldPointers);
            let propagated = this.pointers;
            for (const { offset, length } of extras) {
                const key = this.#nextPointerKey();
                propagated = propagated.set(key, {
                    entity_id: entityId,
                    reference_id: this.reference.reference_id,
                    offset,
                    length,
                    field,
                    ...buildTextQuoteSelector(plainText, offset, length),
                });
            }
            this.pointers = propagated;
        }

        this.#commit(before);
    }

    #createEntity(
        kind: string,
        preferredName: string,
        synonyms?: globalThis.Set<string>,
    ): string {
        const newEntityId = `entity_${crypto.randomUUID()}`;
        this.entities = this.entities.set(newEntityId, {
            entity_id: newEntityId,
            kind,
            preferred_name: preferredName,
            synonyms: synonyms ? Set(synonyms) : Set(),
            confirmed: false,
        });
        return newEntityId;
    }

    #removeEntity(entity_id: string): void {
        if (
            !this.pointers
                .valueSeq()
                .some((pointer) => pointer.entity_id === entity_id)
        ) {
            this.entities = this.entities.delete(entity_id);
        }
    }

    pointer(key: string): Pointer | undefined {
        return this.pointers.get(key);
    }

    entity(entity_id: string): Entity | undefined {
        return this.entities.get(entity_id);
    }

    delete(key: string): void {
        const before = this.#snapshot();
        const entity_id: string | undefined = this.pointers.get(key)?.entity_id;
        this.pointers = this.pointers.delete(key);
        if (entity_id) this.#removeEntity(entity_id);
        this.#commit(before);
    }

    deleteEntity(entityId: string): void {
        const before = this.#snapshot();

        const pointerKeys = this.pointers
            .entrySeq()
            .filter(([, p]) => p.entity_id === entityId)
            .map(([k]) => k)
            .toArray();

        let updatedPointers = this.pointers;
        for (const k of pointerKeys)
            updatedPointers = updatedPointers.delete(k);
        this.pointers = updatedPointers;

        const relationsArray = this.relations.toArray();
        const filteredRelations = relationsArray.filter(
            (r) => r.subject !== entityId && r.object !== entityId,
        );
        this.relations = Set(filteredRelations);

        this.entities = this.entities.delete(entityId);
        this.#commit(before);
    }

    addRelation(subjectId: string, predicate: string, objectId: string): void {
        const before = this.#snapshot();
        this.relations = this.relations.add(
            createRelation({ predicate, subject: subjectId, object: objectId }),
        );
        this.recentPredicates = [
            predicate,
            ...this.recentPredicates.filter((p) => p !== predicate),
        ].slice(0, 10);
        this.#commit(before);
    }

    removeRelation(relation: Relation): void {
        const before = this.#snapshot();
        this.relations = this.relations.delete(relation);
        this.#commit(before);
    }

    updateEntityKind(entity_id: string, kind: string): void {
        const before = this.#snapshot();
        const entity = this.entities.get(entity_id);
        if (entity) {
            this.entities = this.entities.set(entity_id, { ...entity, kind });
            this.#commit(before);
        }
    }

    updateEntityPreferredName(entity_id: string, preferred_name: string): void {
        const before = this.#snapshot();
        const entity = this.entities.get(entity_id);
        if (entity) {
            const trimmed = preferred_name.trim();
            const synonyms =
                trimmed && !entity.synonyms.has(trimmed)
                    ? entity.synonyms.add(trimmed)
                    : entity.synonyms;
            this.entities = this.entities.set(entity_id, {
                ...entity,
                preferred_name,
                synonyms,
            });
            this.#commit(before);
        }
    }

    updateEntityUri(entity_id: string, uri: string): void {
        const before = this.#snapshot();
        const entity = this.entities.get(entity_id);
        if (entity) {
            this.entities = this.entities.set(entity_id, { ...entity, uri });
            this.#commit(before);
        }
    }

    addSynonym(entity_id: string, synonym: string): void {
        const before = this.#snapshot();
        const entity = this.entities.get(entity_id);
        if (entity && synonym.trim()) {
            this.entities = this.entities.set(entity_id, {
                ...entity,
                synonyms: entity.synonyms.add(synonym.trim()),
            });
            this.#commit(before);
        }
    }

    removeSynonym(entity_id: string, synonym: string): void {
        const before = this.#snapshot();
        const entity = this.entities.get(entity_id);
        if (entity) {
            this.entities = this.entities.set(entity_id, {
                ...entity,
                synonyms: entity.synonyms.delete(synonym),
            });
            this.#commit(before);
        }
    }

    /**
     * Adds pointer(s) for an entity identified by a known ID (e.g. an ontology
     * CURIE). If the entity is not yet in local state it is created; otherwise
     * the pointer is appended and the highlighted text added as a synonym.
     * Propagates the annotation to all other identical uncovered occurrences
     * within the same field.
     */
    addWithId(
        entityId: string,
        kind: string,
        preferredName: string,
        offsets: Array<{ offset: number; length: number }>,
        confirmed = true,
        field: "abstract" | "body" = "body",
    ): void {
        const before = this.#snapshot();

        if (!this.entities.has(entityId)) {
            const trimmedName = preferredName.trim();
            this.entities = this.entities.set(entityId, {
                entity_id: entityId,
                kind,
                preferred_name: preferredName,
                synonyms: trimmedName ? Set([trimmedName]) : Set(),
                confirmed,
            });
        }

        const plainText = this.#getPlainText(field);

        let updatedPointers = this.pointers;
        for (const { offset, length } of offsets) {
            const key = this.#nextPointerKey();
            updatedPointers = updatedPointers.set(key, {
                entity_id: entityId,
                reference_id: this.reference.reference_id,
                offset,
                length,
                field,
                ...buildTextQuoteSelector(plainText, offset, length),
            });
        }
        this.pointers = updatedPointers;

        // Propagate to all other identical uncovered occurrences in the same field.
        const searchText = offsets[0]
            ? plainText.slice(
                  offsets[0].offset,
                  offsets[0].offset + offsets[0].length,
              )
            : "";
        if (searchText) {
            const candidates = allOccurrences(plainText, searchText);
            const fieldPointers = this.pointers.filter(
                (p) => p.field === field,
            );
            const extras = uncoveredOffsets(candidates, fieldPointers);
            let propagated = this.pointers;
            for (const { offset, length } of extras) {
                const key = this.#nextPointerKey();
                propagated = propagated.set(key, {
                    entity_id: entityId,
                    reference_id: this.reference.reference_id,
                    offset,
                    length,
                    field,
                    ...buildTextQuoteSelector(plainText, offset, length),
                });
            }
            this.pointers = propagated;
        }

        this.#commit(before);
    }

    updatePointerOffsets(
        pointerId: string,
        offset: number,
        length: number,
    ): void {
        const before = this.#snapshot();
        const pointer = this.pointers.get(pointerId);
        if (pointer) {
            const plainText = this.#getPlainText(pointer.field);
            this.pointers = this.pointers.set(pointerId, {
                ...pointer,
                offset,
                length,
                ...buildTextQuoteSelector(plainText, offset, length),
            });
            this.#commit(before);
        }
    }
}

/**
 * Returns the offset and length of every non-overlapping occurrence of
 * `searchText` within `plainText`, in order of appearance.
 */
export function allOccurrences(
    plainText: string,
    searchText: string,
): Array<{ offset: number; length: number }> {
    if (!searchText) return [];
    const results: Array<{ offset: number; length: number }> = [];
    let idx = 0;
    while ((idx = plainText.indexOf(searchText, idx)) !== -1) {
        results.push({ offset: idx, length: searchText.length });
        idx += searchText.length;
    }
    return results;
}

/**
 * Filters `candidates` to those not overlapping any existing pointer span.
 * Used to avoid creating duplicate annotations when propagating.
 */
export function uncoveredOffsets(
    candidates: Array<{ offset: number; length: number }>,
    againstPointers: ImmutableMap<string, Pointer>,
): Array<{ offset: number; length: number }> {
    return candidates.filter(
        ({ offset, length }) =>
            !againstPointers
                .valueSeq()
                .some(
                    (p) =>
                        p.offset < offset + length &&
                        offset < p.offset + p.length,
                ),
    );
}

/**
 * Extracts the sentence containing the character at `offset` from plain text.
 *
 * Boundary rules: `.!?` only split when followed by whitespace/end-of-string,
 * and not when preceded by a single isolated uppercase letter (abbreviations
 * like "E. coli"). "RyhB. Next" still splits because "B" is not isolated.
 *
 * @returns sentence text (trimmed) and its start offset in the full text.
 */
export function extractSentence(
    plainText: string,
    offset: number,
): { text: string; start: number } {
    function isSentenceBoundary(pos: number): boolean {
        if (!/[.!?]/.test(plainText[pos])) return false;
        const next = plainText[pos + 1];
        if (next !== undefined && !/\s/.test(next)) return false;
        const prev = plainText[pos - 1];
        if (prev && /[A-Z]/.test(prev)) {
            const prevPrev = plainText[pos - 2];
            if (!prevPrev || /\W/.test(prevPrev)) return false;
        }
        return true;
    }

    let start = offset;
    while (start > 0 && !isSentenceBoundary(start - 1)) {
        start--;
    }

    let end = offset;
    while (end < plainText.length && !isSentenceBoundary(end)) {
        end++;
    }
    if (end < plainText.length) end++;

    const raw = plainText.slice(start, end);
    const leadingSpaces = raw.length - raw.trimStart().length;
    return { text: raw.trim(), start: start + leadingSpaces };
}

const _sanitizeCache = new WeakMap<
    HTMLDivElement,
    { html: string; sanitized: string }
>();

/**
 * Renders annotated HTML into `elem`, highlighting only pointers that belong
 * to the given `field`. Uses TextQuoteSelector to resolve offsets robustly.
 *
 * Returns a cleanup that unmounts every `ResourceCard` this call mounted. The
 * caller (the `{@attach}` in `ArticleSection.svelte`) must invoke it before the
 * next render and on destroy: `mount()`ed cards own live `$derived` state that
 * keeps reacting to `AnnotationState` even after `innerHTML` detaches their DOM,
 * so without an explicit `unmount()` they accumulate one leaked instance per
 * card per edit.
 */
export function annotateHTMLString(
    elem: HTMLDivElement,
    html: string,
    pointers: ImmutableMap<string, Pointer>,
    entities: ImmutableMap<string, Entity>,
    field: "abstract" | "body",
): () => void {
    const cached = _sanitizeCache.get(elem);
    const sanitized =
        cached?.html === html
            ? cached.sanitized
            : DOMPurify.sanitize(html, {
                  ADD_TAGS: ["figure", "figcaption", "img"],
                  ADD_ATTR: ["src", "alt"],
              });
    if (cached?.html !== html) {
        _sanitizeCache.set(elem, { html, sanitized });
    }

    elem.replaceChildren();
    elem.innerHTML = sanitized;

    const plainText = elem.textContent || "";
    const fieldPointers = pointers.filter((p) => p.field === field);

    const ranges: Array<AnnotatedRange & { range: Range }> = fieldPointers
        .entrySeq()
        .map(([key, pointer]) => {
            const resolved = resolvePointerOffset(pointer, plainText);
            if (!resolved) return { range: null, pointer_id: key, label: "" };
            return {
                range: createRangeFromOffsets(
                    elem,
                    resolved.offset,
                    resolved.offset + resolved.length,
                ),
                pointer_id: key,
                label: entities.get(pointer.entity_id)?.kind || "",
            };
        })
        .filter(
            (ar): ar is AnnotatedRange & { range: Range } => ar.range !== null,
        )
        .toArray();
    const mounted = ranges.map((range) => markRange(elem, range));

    return () => {
        for (const instance of mounted) unmount(instance);
    };
}

function markRange(
    elem: HTMLElement,
    pointer: AnnotatedRange & { range: Range },
): Record<string, unknown> {
    const doc = elem.ownerDocument;
    const mark = doc.createElement("span");
    mark.id = pointer.pointer_id;

    const fragment = pointer.range.extractContents();
    const instance = mount(ResourceCard, {
        target: mark,
        props: { fragment, pointer_id: pointer.pointer_id },
    });
    pointer.range.insertNode(mark);
    pointer.range.detach?.();
    return instance;
}

function getTextNodes(element: HTMLElement): Text[] {
    const textNodes: Text[] = [];
    const treeWalker = element.ownerDocument.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
    );

    let node: Node | null;
    while ((node = treeWalker.nextNode())) {
        textNodes.push(node as Text);
    }

    return textNodes;
}

export function createRangeFromOffsets(
    element: HTMLElement,
    startOffset: number,
    endOffset: number,
): Range | null {
    element.normalize();

    const textNodes = getTextNodes(element);
    let currentOffset = 0;
    let startNode: Text | null = null;
    let endNode: Text | null = null;
    let startNodeOffset = 0;
    let endNodeOffset = 0;

    for (const node of textNodes) {
        const nodeLength = node.length;

        if (currentOffset + nodeLength > startOffset && !startNode) {
            startNode = node;
            startNodeOffset = startOffset - currentOffset;
        }

        if (currentOffset + nodeLength >= endOffset && !endNode) {
            endNode = node;
            endNodeOffset = endOffset - currentOffset;
            break;
        }

        currentOffset += nodeLength;
    }

    if (startNode && endNode) {
        const range = element.ownerDocument.createRange();
        range.setStart(startNode, startNodeOffset);
        range.setEnd(endNode, endNodeOffset);
        return range;
    }

    return null;
}
