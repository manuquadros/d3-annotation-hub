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
}

interface Snapshot {
    entities: ImmutableMap<string, Entity>;
    pointers: ImmutableMap<string, Pointer>;
    relations: ImmutableSet<Relation>;
}

const CONTEXT_SIZE = 32;

/** Cap on retained undo snapshots; oldest are dropped past this. */
const MAX_UNDO_HISTORY = 100;

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

    pointerCountByEntity = $derived.by(() => {
        const counts = new globalThis.Map<string, number>();
        for (const p of this.pointers.values()) {
            counts.set(p.entity_id, (counts.get(p.entity_id) ?? 0) + 1);
        }
        return counts;
    });

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
        const past = [...this.#past, snapshot];
        if (past.length > MAX_UNDO_HISTORY) {
            past.splice(0, past.length - MAX_UNDO_HISTORY);
        }
        this.#past = past;
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

    #plainTextCache = new globalThis.Map<"abstract" | "body", string>();

    /**
     * Sanitized plain text of the given field, memoized. The reference body and
     * abstract are immutable for an instance's lifetime, so each field is
     * sanitized at most once rather than on every selection, highlight click,
     * or edit.
     */
    plainText(field: "abstract" | "body"): string {
        const cached = this.#plainTextCache.get(field);
        if (cached !== undefined) return cached;

        const html =
            field === "abstract"
                ? this.reference.abstract
                : this.reference.body;
        let text = "";
        const tempDiv = html ? globalThis.document?.createElement("div") : null;
        if (tempDiv) {
            tempDiv.innerHTML = DOMPurify.sanitize(html!);
            text = tempDiv.textContent || "";
        }
        this.#plainTextCache.set(field, text);
        return text;
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
        const plainText = this.plainText(field);
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

        const plainText = this.plainText(field);

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

        const plainText = this.plainText(field);

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
            const plainText = this.plainText(pointer.field);
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
    const spans = againstPointers
        .valueSeq()
        .map((p) => ({ start: p.offset, end: p.offset + p.length }))
        .toArray()
        .sort((a, b) => a.start - b.start);
    const starts = spans.map((s) => s.start);
    // maxEndUpTo[i] = greatest span end among spans[0..i], so a candidate can
    // test for any overlap with two binary searches instead of scanning spans.
    const maxEndUpTo = new Array<number>(spans.length);
    let running = -Infinity;
    for (let i = 0; i < spans.length; i++) {
        running = Math.max(running, spans[i].end);
        maxEndUpTo[i] = running;
    }

    return candidates.filter(({ offset, length }) => {
        const end = offset + length;
        // A span overlaps iff it starts before `end` and ends after `offset`.
        const startingBefore = firstIndexWhere(starts, (s) => s >= end);
        return startingBefore === 0 || maxEndUpTo[startingBefore - 1] <= offset;
    });
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

interface Span {
    start: number;
    end: number;
}

interface MarkedSpan extends Span {
    mark: HTMLSpanElement;
    instance: Record<string, unknown>;
    /**
     * The article nodes `markRange` lifted out of the document, in order.
     * `ResourceCard` appends them into its own root, so removing a mark has to
     * put them back before `unmount()` takes that subtree down with them.
     */
    content: Node[];
    /**
     * Whether the marked range lay inside a single text node. If it did not,
     * `extractContents` cloned the partially covered ancestors and left the
     * originals behind empty, which putting `content` back would not undo — so
     * such a mark can only be removed by rebuilding.
     */
    simple: boolean;
}

function spanKey(span: Span): string {
    return `${span.start}:${span.end}`;
}

/**
 * Whether a set of resolved spans can be maintained by patching individual
 * marks. Overlapping spans nest or interleave their marks and empty spans have
 * no stable insertion point, so in either case adding or removing one span
 * would disturb its neighbours' DOM — those states are rebuilt wholesale
 * instead (see TICKET-35 for the overlap semantics themselves).
 */
function spansPatchable(spans: Span[]): boolean {
    const sorted = [...spans].sort((a, b) => a.start - b.start);
    for (let i = 0; i < sorted.length; i++) {
        if (sorted[i].end <= sorted[i].start) return false;
        if (i > 0 && sorted[i].start < sorted[i - 1].end) return false;
    }
    return true;
}

/**
 * Renders an article field's HTML into `elem` and keeps its highlight marks in
 * sync with a pointer map.
 *
 * The first `update()` parses the sanitized HTML and marks every pointer.
 * Later `update()` calls diff the resolved spans against the marks already in
 * the DOM and touch only the ones that changed, so an edit that adds or deletes
 * a single annotation leaves every other mark — and its mounted `ResourceCard`,
 * with its live `$derived` state — exactly where it was. Rebuilding wholesale
 * would instead reparse the article and unmount/remount every card per
 * keystroke-sized edit.
 *
 * Marks reflect pointer positions only, not entity metadata: labels and colors
 * are rendered inside each `ResourceCard`.
 *
 * The owner (the `{@attach}` in `ArticleSection.svelte`) must call `destroy()`
 * on teardown. `mount()`ed cards keep reacting to `AnnotationState` even after
 * their DOM is detached, so without an explicit `unmount()` they leak.
 */
export class ArticleRenderer {
    readonly #elem: HTMLDivElement;
    readonly #field: "abstract" | "body";
    readonly #sanitized: string;

    /** Text of the sanitized HTML, captured before any mark wrapped it. */
    #plainText = "";
    #marks = new globalThis.Map<string, MarkedSpan>();
    /**
     * Pointer key → `spanKey` of spans that resolved against the plain text but
     * could not be turned into a Range. Remembering them keeps an update with
     * no real change from re-attempting (and re-diffing) them every time.
     */
    #unrenderable = new globalThis.Map<string, string>();
    #rendered = false;
    #patchable = false;

    constructor(
        elem: HTMLDivElement,
        html: string,
        field: "abstract" | "body",
    ) {
        this.#elem = elem;
        this.#field = field;
        const cached = _sanitizeCache.get(elem);
        if (cached?.html === html) {
            this.#sanitized = cached.sanitized;
        } else {
            this.#sanitized = DOMPurify.sanitize(html, {
                ADD_TAGS: ["figure", "figcaption", "img"],
                ADD_ATTR: ["src", "alt"],
            });
            _sanitizeCache.set(elem, { html, sanitized: this.#sanitized });
        }
    }

    update(pointers: ImmutableMap<string, Pointer>): void {
        const fieldPointers = pointers.filter((p) => p.field === this.#field);
        if (!this.#rendered || !this.#patchable) {
            this.#fullRender(fieldPointers);
            return;
        }

        // Resolution uses the plain text captured at parse time rather than the
        // live textContent: the marked DOM carries the same characters, but
        // reading it back would make every update O(nodes).
        const desired = new globalThis.Map<string, Span>();
        for (const [key, pointer] of fieldPointers) {
            const resolved = resolvePointerOffset(pointer, this.#plainText);
            if (!resolved) continue;
            desired.set(key, {
                start: resolved.offset,
                end: resolved.offset + resolved.length,
            });
        }
        if (!spansPatchable([...desired.values()])) {
            this.#fullRender(fieldPointers);
            return;
        }

        this.#patch(desired, fieldPointers);
    }

    destroy(): void {
        for (const record of this.#marks.values()) unmount(record.instance);
        this.#marks.clear();
        this.#unrenderable.clear();
        this.#rendered = false;
    }

    #patch(
        desired: globalThis.Map<string, Span>,
        fieldPointers: ImmutableMap<string, Pointer>,
    ): void {
        const stale: string[] = [];
        for (const [key, record] of this.#marks) {
            const span = desired.get(key);
            if (!span || span.start !== record.start || span.end !== record.end)
                stale.push(key);
        }

        const fresh: Array<[string, Span]> = [];
        for (const [key, span] of desired) {
            const record = this.#marks.get(key);
            if (record) {
                if (record.start === span.start && record.end === span.end)
                    continue;
            } else if (this.#unrenderable.get(key) === spanKey(span)) {
                continue;
            }
            fresh.push([key, span]);
        }

        for (const key of [...this.#unrenderable.keys()]) {
            const span = desired.get(key);
            if (!span || this.#unrenderable.get(key) !== spanKey(span))
                this.#unrenderable.delete(key);
        }

        if (stale.length === 0 && fresh.length === 0) return;

        for (const key of stale) {
            if (!this.#marks.get(key)?.simple) {
                this.#fullRender(fieldPointers);
                return;
            }
        }

        // Safety net: if anything replaced the container's children behind the
        // renderer's back, the recorded marks are detached and patching would
        // build a tree a rebuild never would.
        for (const record of this.#marks.values()) {
            if (!this.#elem.contains(record.mark)) {
                this.#fullRender(fieldPointers);
                return;
            }
        }

        for (const key of stale) {
            const record = this.#marks.get(key);
            if (!record) continue;
            unmarkSpan(record);
            this.#marks.delete(key);
        }
        // Restoring a mark's content leaves it split from its neighbours; a
        // rebuild would have parsed one run, and every offset lookup below
        // assumes the merged form.
        if (stale.length > 0) this.#elem.normalize();

        if (fresh.length > 0) this.#markSpans(fresh);
    }

    #fullRender(fieldPointers: ImmutableMap<string, Pointer>): void {
        this.destroy();

        this.#elem.replaceChildren();
        this.#elem.innerHTML = this.#sanitized;
        this.#plainText = this.#elem.textContent || "";

        const resolved: Array<[string, Span]> = [];
        for (const [key, pointer] of fieldPointers) {
            const offsets = resolvePointerOffset(pointer, this.#plainText);
            if (!offsets) continue;
            resolved.push([
                key,
                {
                    start: offsets.offset,
                    end: offsets.offset + offsets.length,
                },
            ]);
        }
        this.#patchable = spansPatchable(resolved.map(([, span]) => span));

        this.#markSpans(resolved);
        this.#rendered = true;
    }

    /**
     * Marks every span in `spans`, which must be disjoint from each other and
     * from the marks already present. All ranges are resolved against a single
     * text-node index before any of them mutates the DOM; the live Ranges track
     * the splits that marking causes.
     */
    #markSpans(spans: Array<[string, Span]>): void {
        const index = buildTextNodeIndex(this.#elem);
        const pending: Array<[string, Span, Range]> = [];
        for (const [key, span] of spans) {
            const range = createRangeFromOffsets(
                this.#elem,
                span.start,
                span.end,
                index,
            );
            if (!range) {
                this.#unrenderable.set(key, spanKey(span));
                continue;
            }
            pending.push([key, span, range]);
        }
        for (const [key, span, range] of pending) {
            this.#marks.set(key, {
                ...markRange(this.#elem, { range, pointer_id: key }),
                start: span.start,
                end: span.end,
            });
        }
    }
}

/**
 * Renders `html` into `elem` with every `field` pointer marked, and returns a
 * cleanup that unmounts the `ResourceCard`s it mounted. This is the one-shot
 * form of {@link ArticleRenderer}; callers that re-render on pointer edits
 * should hold an `ArticleRenderer` instead, so those edits can be patched in.
 */
export function annotateHTMLString(
    elem: HTMLDivElement,
    html: string,
    pointers: ImmutableMap<string, Pointer>,
    field: "abstract" | "body",
): () => void {
    const renderer = new ArticleRenderer(elem, html, field);
    renderer.update(pointers);
    return () => renderer.destroy();
}

function markRange(
    elem: HTMLElement,
    pointer: AnnotatedRange & { range: Range },
): Omit<MarkedSpan, "start" | "end"> {
    const doc = elem.ownerDocument;
    const mark = doc.createElement("span");
    mark.id = pointer.pointer_id;

    const simple = pointer.range.startContainer === pointer.range.endContainer;
    const fragment = pointer.range.extractContents();
    const content = Array.from(fragment.childNodes);
    const instance = mount(ResourceCard, {
        target: mark,
        props: { fragment, pointer_id: pointer.pointer_id },
    });
    pointer.range.insertNode(mark);
    pointer.range.detach?.();
    return { mark, instance, content, simple };
}

function unmarkSpan(record: MarkedSpan): void {
    if (record.mark.parentNode) record.mark.replaceWith(...record.content);
    unmount(record.instance);
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

/**
 * A snapshot of `element`'s text nodes with their cumulative plain-text end
 * offsets, enabling binary-search offset lookups. Build once per DOM state and
 * pass to `createRangeFromOffsets` to avoid re-walking the tree per pointer.
 * Invalidated by any DOM mutation (e.g. a `Range.extractContents()`).
 */
export interface TextNodeIndex {
    nodes: Text[];
    /** `starts[i]` is the plain-text offset at which `nodes[i]` begins. */
    starts: number[];
    /** `ends[i] === starts[i] + nodes[i].length`; strictly increasing. */
    ends: number[];
}

export function buildTextNodeIndex(element: HTMLElement): TextNodeIndex {
    element.normalize();
    const nodes = getTextNodes(element);
    const starts = new Array<number>(nodes.length);
    const ends = new Array<number>(nodes.length);
    let acc = 0;
    for (let i = 0; i < nodes.length; i++) {
        starts[i] = acc;
        acc += nodes[i].length;
        ends[i] = acc;
    }
    return { nodes, starts, ends };
}

/**
 * First index `i` where `test(values[i])` holds, or `values.length` if none.
 * `values` must be sorted so `test` flips from false to true exactly once.
 */
function firstIndexWhere(
    values: number[],
    test: (value: number) => boolean,
): number {
    let lo = 0;
    let hi = values.length;
    while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (test(values[mid])) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}

export function createRangeFromOffsets(
    element: HTMLElement,
    startOffset: number,
    endOffset: number,
    index?: TextNodeIndex,
): Range | null {
    const { nodes, starts, ends } = index ?? buildTextNodeIndex(element);
    if (nodes.length === 0) return null;

    const startIdx = firstIndexWhere(ends, (e) => e > startOffset);
    const endIdx = firstIndexWhere(ends, (e) => e >= endOffset);
    if (startIdx >= nodes.length || endIdx >= nodes.length) return null;

    const range = element.ownerDocument.createRange();
    range.setStart(nodes[startIdx], startOffset - starts[startIdx]);
    range.setEnd(nodes[endIdx], endOffset - starts[endIdx]);
    return range;
}
