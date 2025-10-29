import type { Entity, Relation, Pointer } from "$lib/types.ts";

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
    entities: Map<string, Entity>,
    pointers: Map<number, Pointer>,
): HTMLElement {
    elem.replaceChildren();
    elem.innerHTML = html;

    const doc = elem.ownerDocument;

    const b = doc.createElement("b");
    const range = rangeFromPointer(elem, pointers.get(1));

    try {
        range.surroundContents(b);
    } catch {
        // Fallback in case the range partially selects non-Text nodes
        const fragment = range.extractContents();
        b.appendChild(fragment);
        range.insertNode(b);
    } finally {
        range.detach?.();
    }
}

/**
 * Get range  object from input pointer directions.
 *
 * @param pointer - input Pointer object
 * @returns a Range object
 */
function rangeFromPointer(anchor: HTMLElement, pointer: Pointer): Range {
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
