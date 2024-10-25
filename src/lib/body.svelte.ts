import { writable, derived, get } from "svelte/store";
import type { Readable, Writable } from "svelte/store";

import { isValidEntitySpan, newSpan, wrapRange, entID } from "$lib/utils.ts";
import {
    resourceStore,
    nextResourceID,
    type Resource,
} from "$lib/resources.svelte.ts";
import { RelationStore } from "$lib/relations.svelte.ts";
import { rangeToClass } from "$lib/ranges.ts";

export class bodyStore {
    content: Element | undefined = $state();
    entspans: Map<string, HTMLSpanElement> = $derived.by(() =>
        this.getEntitySpans(),
    );
    resources: Map<string, Resource> = $derived.by(() =>
        resourceStore(this.entspans),
    );
    relations: RelationStore;

    classes: Set<string> = $derived(
        new Set(Array.from(this.resources.values()).map((res) => res.label)),
    );

    nextResourceId: string = $derived.by(() => nextResourceID(this.resources));

    selectedSpan: HTMLSpanElement | null = null;

    constructor(chunk: Element) {
        // Initialize all entity spans, making sure they have an ID and a button.
        this.content = chunk;
        const spans = this.content.querySelectorAll("span");

        spans.forEach((span) => {
            span.id = String(entID());
        });
        this.relations = new RelationStore(this.resources);
    }

    get spans() {
        return Array.from(this.entspans.values());
    }

    getEntitySpans() {
        if (this.content) {
            let spans = Array.from(this.content.querySelectorAll("span"));
            spans = spans.filter((span) => isValidEntitySpan(span));
            const spanMap = new Map(spans.map((span) => [span.id, span]));
            return spanMap;
        } else {
            return new Map();
        }
    }

    // TODO: update the relations store as well!
    mergeResources(
        _source: string | Resource,
        _target: string | Resource,
    ): void {
        const source = this.getResource(_source);
        const target = this.getResource(_target);

        if (source && source.label === target?.label)
            this.replaceResource(source, target);
    }

    getResource(res: string | Resource): Resource | undefined {
        return typeof res === "string" ? this.resources.get(res) : res;
    }

    removeAnnotation(id: string) {
        const span = this.content?.querySelector(`#${CSS.escape(id)}`);
        const parent = span?.parentNode as Node;

        if (span) {
            span.childNodes.forEach((node) => {
                if (node.nodeName === "BUTTON") {
                    node.childNodes.forEach((child) =>
                        parent.insertBefore(child, span),
                    );
                } else {
                    parent.insertBefore(node, span);
                }
            });
            parent.removeChild(span);
        }
    }

    removeAnnotations(ids: string[] | Set<string>): void {
        ids.forEach(this.removeAnnotation);
    }

    removeResource(resource: string | HTMLSpanElement): void {
        if (resource instanceof HTMLSpanElement)
            resource = resource.getAttribute("resource") || "";

        const spans = this.spans.filter(
            (span) => span.getAttribute("resource") === resource,
        );

        this.removeAnnotations(spans.map((span) => span.id as string));
    }

    annotateRange(label: string, range: Range) {
        const span = newSpan(
            label,
            rangeToClass(range, "entity"),
            this.nextResourceId,
        );

        range.surroundContents(span);

        queueMicrotask(() => {
            const chunkBody = document.querySelector(".chunk-body");
            if (chunkBody) {
                this.content = chunkBody.cloneNode(true) as Element;
            }
        });
        //propagate
    }

    replaceResource(
        _source: string | Resource,
        _target: string | Resource,
    ): void {
        const source =
            typeof _source === "string" ? _source : _source.resourceid;
        const target =
            typeof _target === "string" ? _target : _target.resourceid;

        const content = this.content?.cloneNode(true) as Element;

        const spans = content?.querySelectorAll(`span[resource="${source}"]`);

        spans?.forEach((span) => span.setAttribute("resource", target));

        this.content = content;
    }

    propagate(resource: Resource): void {
        function getRange(
            startIndex: number,
            endIndex: number,
            textNode: Text,
        ): Range {
            const range = document.createRange();
            range.setStart(textNode, startIndex);
            range.setEnd(textNode, Math.min(endIndex, textNode.length));
            return range;
        }

        if (this.content) {
            const textNodes = getAllTextNodes(this.content);

            for (let i = 0; i < textNodes.length; i++) {
                let textNode = textNodes[i];
                let text = textNode.textContent || "";

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
                            textNode = span.nextSibling as Text;
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
    }
}

function getAllTextNodes(element: Element): Text[] {
    const textNodes: Text[] = [];
    const treeWalker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);

    let node: Node | null;
    while ((node = treeWalker.nextNode())) {
        textNodes.push(node as Text);
    }

    return textNodes;
}

// Helper function to escape special characters in string for use in regex
function escapeRegExp(string: string): string {
    return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isWithinEntitySpan(range: Range): boolean {
    let node: Node | null = range.commonAncestorContainer;
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
