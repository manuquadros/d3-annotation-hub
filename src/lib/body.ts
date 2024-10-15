import { writable, derived, get } from "svelte/store";
import type { Readable } from "svelte/store";

import {
    isValidEntitySpan,
    spanWrappedButton,
    newSpan,
    wrapRange,
    entID,
} from "$lib/utils.ts";
import { resources } from "$lib/resources.ts";
import type { Resource } from "$lib/resources.ts";
import { rangeToClass } from "$lib/ranges.ts";

const { subscribe, set, update } = writable<Element>();

export const body = {
    subscribe,
    set,
    replaceResource: _replaceResource,
    propagate: _propagate,

    initialize(): void {
        get(entitySpans).forEach((span) => {
            span.id = String(entID());
            resources.storeEntitySpan(span);
            spanWrappedButton(span);
        });
    },
};

export const entitySpans: Readable<HTMLSpanElement[]> = derived(
    body,
    ($body) => {
        const spans = Array.from($body.querySelectorAll("span"));
        return spans.filter(isValidEntitySpan);
    },
);

function _replaceResource(source: string, target: string): void {
    update((body) => {
        const spans = body.querySelectorAll(`span[resource="${source}"]`);

        spans.forEach((span) => span.setAttribute("resource", target));

        return body;
    });
}

export async function annotateRange(
    label: string,
    range: Range,
): Promise<{ button: HTMLButtonElement; resource: Resource }> {
    let span = newSpan(label, rangeToClass(range, "entity"));

    range.surroundContents(span);
    const resource = await resources.storeEntitySpan(span);
    body.propagate(resource);

    const button = spanWrappedButton(span);

    return { button, resource };
}

function _propagate(resource: Resource): void {
    const getRange = function (startIndex, endIndex, textNode) {
        const range = document.createRange();
        range.setStart(textNode, startIndex);
        range.setEnd(textNode, Math.min(endIndex, textNode.length));
        return range;
    };

    update((body) => {
        if (body) {
            const textNodes = getAllTextNodes(body);

            for (let i = 0; i < textNodes.length; i++) {
                let textNode = textNodes[i];
                let text = textNode.textContent;

                for (const name of resource.names) {
                    const regex = new RegExp(
                        `\\b${escapeRegExp(name)}\\b`,
                        "gi",
                    );
                    let match;

                    while ((match = regex.exec(text)) !== null) {
                        const range = getRange(
                            match.index,
                            regex.lastIndex,
                            textNode,
                        );

                        if (!isWithinEntitySpan(range)) {
                            const span = wrapRange(range, resource);

                            // Update text node reference and content
                            textNode = span.nextSibling as Node;
                            if (
                                !textNode ||
                                textNode.nodeType !== Node.TEXT_NODE
                            )
                                break; // No more text in this node
                            text = textNode.textContent || "";
                            // Reset regex to search from the beginning of the new text
                            regex.lastIndex = 0;
                        }
                    }
                }
            }
        }
        return body;
    });
}

function getAllTextNodes(element: Element): Node[] {
    const textNodes: Node[] = [];
    const treeWalker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);

    let node: Node | null;
    while ((node = treeWalker.nextNode())) {
        textNodes.push(node);
    }

    return textNodes;
}

// Helper function to escape special characters in string for use in regex
function escapeRegExp(string: string): string {
    return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isWithinEntitySpan(range: Range): boolean {
    let node = range.commonAncestorContainer;
    while (node && node !== document.body) {
        if (
            node.nodeType === Node.ELEMENT_NODE &&
            (node as Element).tagName === "SPAN" &&
            isValidEntitySpan(node as HTMLSpanElement)
        ) {
            return true;
        }
        node = node.parentNode;
    }
    return false;
}
