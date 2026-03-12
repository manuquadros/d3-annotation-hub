import type { Relation, Pointer, User, Reference, Entity } from "$lib/types.ts";
import { AnnotationStateSchema, nextPointerKey } from "$lib/types.ts";
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
        this.entities = validated.entities;
        this.pointers = validated.pointers;
        this.relations = validated.relations;
        this.completed = validated.completed;
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
     * Label `offsets` with `label`, adding an entity and pointers to the state.
     */
    add(
        label: string,
        offsets: Array<{ offset: number; length: number }>,
    ): void {
        const before = this.#snapshot();

        // Extract designations from the body text at each offset
        const designations = new globalThis.Set<string>();
        const body = this.reference.body;

        if (body) {
            const tempDiv = globalThis.document?.createElement("div");
            if (tempDiv) {
                tempDiv.innerHTML = DOMPurify.sanitize(body);
                const plainText = tempDiv.textContent || "";

                for (const { offset, length } of offsets) {
                    const text = plainText.slice(offset, offset + length);
                    if (text) {
                        designations.add(text);
                    }
                }
            }
        }

        const newEntityId = this.#addEntity(label, designations);

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

    #addEntity(label: string, designations?: globalThis.Set<string>): string {
        const newEntityId = `entity_${Date.now()}_${Math.random().toString(36).substring(7)}`;
        this.entities = this.entities.set(newEntityId, {
            entity_id: newEntityId,
            kind: label,
            designations: designations ? Set(designations) : undefined,
        });
        return newEntityId;
    }

    /**
     * Removes the `entity_id` entry from the entities Map if it is not
     * referenced by any pointer.
     */
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

    updateEntityKind(entity_id: string, kind: string): void {
        const before = this.#snapshot();
        const entity = this.entities.get(entity_id);
        if (entity) {
            this.entities = this.entities.set(entity_id, { ...entity, kind });
            this.#commit(before);
        }
    }
}

/**
 * Returns an HTMLElement annotated according to the state parameters.
 *
 * @param html - initial document to be annotated
 * @param entities - Mapping of entities in the current annotation state
 * @param pointers - Mapping of pointers in the current annotation state
 * @returns HTMLElement with buttons corresponding to the pointers
 */
export function annotateHTMLString(
    elem: HTMLDivElement,
    html: string,
    annotationState: AnnotationState,
): void {
    elem.replaceChildren();
    elem.innerHTML = DOMPurify.sanitize(html);
    const pointers = annotationState.pointers;
    const entities = annotationState.entities;

    // Build array here instead of an iterator, because we want to compute all
    // ranges before manipulating the DOM.
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

/**
 * Get range object from input pointer directions.
 *
 * @param pointer - input Pointer object
 * @returns a Range object
 */
function rangeFromPointer(anchor: HTMLElement, pointer: Pointer): Range | null {
    return createRangeFromOffsets(
        anchor,
        pointer.offset,
        pointer.offset + pointer.length,
    );
}

/**
 * Returns an array containing the Text nodes present in the input element.
 *
 * @param element - input element
 * @returns array of Text nodes
 */
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
 * Returns a Range object locating a piece of text inside of the input element.
 *
 * @param element - input element
 * @param startOffset - initial position of the offset
 * @param endOffset - final position of the offset
 * @returns a Range, if the offsets are within the boundaries of the input
       element.
 */
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

        // Check if the start offset is within this node
        if (currentOffset + nodeLength >= startOffset && !startNode) {
            startNode = node;
            startNodeOffset = startOffset - currentOffset;
        }

        // Check if the end offset is within this node
        if (currentOffset + nodeLength >= endOffset && !endNode) {
            endNode = node;
            endNodeOffset = endOffset - currentOffset;
            break; // We can stop once we find both nodes
        }

        currentOffset += nodeLength;
    }

    if (startNode && endNode) {
        const range = element.ownerDocument.createRange();
        range.setStart(startNode, startNodeOffset);
        range.setEnd(endNode, endNodeOffset);
        return range;
    }

    return null; // Return null if the range could not be created
}
