import type { Relation, Pointer, User, Reference, Entity } from "$lib/types.ts";
import { AnnotationStateSchema } from "$lib/types.ts";
import { nextPointerKey, initPointerCounter } from "$lib/pointers.ts";
import { mount } from "svelte";
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


export class AnnotationState {
    user: User;
    reference: Reference;
    project_id!: number;
    entities: ImmutableMap<string, Entity> = $state(Map());
    pointers: ImmutableMap<string, Pointer> = $state(Map());
    relations: ImmutableSet<Relation> = $state(Set());
    completed: boolean = $state(false);

    #past: Snapshot[] = $state([]);
    #future: Snapshot[] = $state([]);

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
        initPointerCounter(this.pointers.size);
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

    /**
     * Creates a new entity with the given kind and preferred name, then creates
     * pointers at each offset. The text at each offset is added as a synonym.
     */
    add(
        kind: string,
        preferredName: string,
        offsets: Array<{ offset: number; length: number }>,
    ): void {
        const before = this.#snapshot();
        const body = this.reference.body;
        const synonyms = new globalThis.Set<string>();

        // Always include the preferred name itself as a synonym.
        const trimmedName = preferredName.trim();
        if (trimmedName) synonyms.add(trimmedName);

        if (body) {
            const tempDiv = globalThis.document?.createElement("div");
            if (tempDiv) {
                tempDiv.innerHTML = DOMPurify.sanitize(body);
                const plainText = tempDiv.textContent || "";
                for (const { offset, length } of offsets) {
                    const text = plainText.slice(offset, offset + length).trim();
                    if (text) synonyms.add(text);
                }
            }
        }

        const newEntityId = this.#createEntity(kind, preferredName, synonyms);

        let updatedPointers = this.pointers;
        for (const { offset, length } of offsets) {
            const key = nextPointerKey();
            updatedPointers = updatedPointers.set(key, {
                entity_id: newEntityId,
                reference_id: this.reference.reference_id,
                offset,
                length,
            });
        }

        this.pointers = updatedPointers;
        this.#commit(before);
    }

    /**
     * Adds new pointer(s) to an existing entity and appends the highlighted
     * text as a synonym if it isn't already present.
     */
    addToExistingEntity(
        entityId: string,
        synonym: string,
        offsets: Array<{ offset: number; length: number }>,
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

        let updatedPointers = this.pointers;
        for (const { offset, length } of offsets) {
            const key = nextPointerKey();
            updatedPointers = updatedPointers.set(key, {
                entity_id: entityId,
                reference_id: this.reference.reference_id,
                offset,
                length,
            });
        }

        this.pointers = updatedPointers;
        this.#commit(before);
    }

    #createEntity(
        kind: string,
        preferredName: string,
        synonyms?: globalThis.Set<string>,
    ): string {
        const newEntityId = `entity_${Date.now()}_${Math.random().toString(36).substring(7)}`;
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
        const entity_id: string | undefined =
            this.pointers.get(key)?.entity_id;
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
        for (const k of pointerKeys) updatedPointers = updatedPointers.delete(k);
        this.pointers = updatedPointers;

        const relationsArray = this.relations.toArray();
        const filteredRelations = relationsArray.filter(
            (r) => r.subject !== entityId && r.object !== entityId,
        );
        this.relations = Set(filteredRelations);

        this.entities = this.entities.delete(entityId);
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
            const synonyms = trimmed && !entity.synonyms.has(trimmed)
                ? entity.synonyms.add(trimmed)
                : entity.synonyms;
            this.entities = this.entities.set(entity_id, { ...entity, preferred_name, synonyms });
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
     * CURIE). If the entity is not yet in the local state it is created with the
     * given kind and preferredName; if it already exists the pointer is simply
     * appended and the highlighted text is added as a synonym.
     */
    addWithId(
        entityId: string,
        kind: string,
        preferredName: string,
        offsets: Array<{ offset: number; length: number }>,
        confirmed = true,
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

        let updatedPointers = this.pointers;
        for (const { offset, length } of offsets) {
            const key = nextPointerKey();
            updatedPointers = updatedPointers.set(key, {
                entity_id: entityId,
                reference_id: this.reference.reference_id,
                offset,
                length,
            });
        }

        this.pointers = updatedPointers;
        this.#commit(before);
    }

    updatePointerOffsets(pointerId: string, offset: number, length: number): void {
        const before = this.#snapshot();
        const pointer = this.pointers.get(pointerId);
        if (pointer) {
            this.pointers = this.pointers.set(pointerId, { ...pointer, offset, length });
            this.#commit(before);
        }
    }
}

/**
 * Extracts the sentence containing the character at `offset` from plain text.
 * Returns the sentence string and its start offset in the full text.
 */
export function extractSentence(
    plainText: string,
    offset: number,
): { text: string; start: number } {
    const sentenceEnders = /[.!?]/;
    let start = offset;
    while (start > 0 && !sentenceEnders.test(plainText[start - 1])) {
        start--;
    }
    let end = offset;
    while (end < plainText.length && !sentenceEnders.test(plainText[end])) {
        end++;
    }
    if (end < plainText.length) end++; // include the punctuation

    const raw = plainText.slice(start, end);
    const leadingSpaces = raw.length - raw.trimStart().length;
    return { text: raw.trim(), start: start + leadingSpaces };
}

/**
 * Returns an HTMLElement annotated according to the state parameters.
 */
export function annotateHTMLString(
    elem: HTMLDivElement,
    html: string,
    pointers: ImmutableMap<string, Pointer>,
    entities: ImmutableMap<string, Entity>,
): void {
    elem.replaceChildren();
    elem.innerHTML = DOMPurify.sanitize(html);

    const ranges: Array<AnnotatedRange & { range: Range }> = pointers
        .entrySeq()
        .map(([key, pointer]) => {
            return {
                range: rangeFromPointer(elem, pointer),
                pointer_id: key,
                label: entities.get(pointer.entity_id)?.kind || "",
            };
        })
        .filter((ar): ar is AnnotatedRange & { range: Range } => ar.range !== null)
        .toArray();
    ranges.forEach((range) => markRange(elem, range));
}

function markRange(elem: HTMLElement, pointer: AnnotatedRange & { range: Range }) {
    const doc = elem.ownerDocument;
    const mark = doc.createElement("span");
    mark.id = pointer.pointer_id;

    const fragment = pointer.range.extractContents();
    mount(ResourceCard, {
        target: mark,
        props: { fragment, pointer_id: pointer.pointer_id },
    });
    pointer.range.insertNode(mark);
    pointer.range.detach?.();
}

function rangeFromPointer(anchor: HTMLElement, pointer: Pointer): Range | null {
    return createRangeFromOffsets(
        anchor,
        pointer.offset,
        pointer.offset + pointer.length,
    );
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

function createRangeFromOffsets(
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
