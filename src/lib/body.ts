import { writable, derived, get } from "svelte/store";
import type { Readable, Writable } from "svelte/store";

import { isValidEntitySpan, newSpan, wrapRange, entID } from "$lib/utils.ts";
import { resourceStore } from "$lib/resources.ts";
import type { Resource } from "$lib/resources.ts";
import { RelationStore } from "$lib/relations.ts";
import { rangeToClass } from "$lib/ranges.ts";

export class bodyStore implements Writable<Element> {
    entspans: Readable<Map<string, HTMLSpanElement>>;
    spans: HTMLSpanElement[] = [];
    resources: Readable<Map<string, Resource>>;
    relations: RelationStore;
    classes: Set<string>;
    subscribe;
    update;
    set;

    constructor(content: Element) {
        // Initialize all entity spans, making sure they have an ID and a button.
        const spans = content.querySelectorAll("span");

        spans.forEach((span) => {
            span.id = String(entID());
        });

        // Initialize the body store proper
        const body = writable(content);
        const { subscribe, set, update } = body;
        this.subscribe = subscribe;
        this.update = update;
        this.set = set;

        // Initialize stores for entity spans, resources and relations
        this.entspans = derived(body, (body) => {
            let spans = Array.from(body.querySelectorAll("span"));
            spans = spans.filter((span) => isValidEntitySpan(span));
            return new Map(spans.map((span) => [span.id, span]));
        });
        this.resources = resourceStore(this.entspans);
        this.relations = new RelationStore(this.resources);

        // Create subscriptions for this.classes and this.spans
        this.classes = new Set();
        this.resources.subscribe((resources) =>
            resources.forEach((res) => this.classes.add(res.label)),
        );

        this.entspans.subscribe(
            (spans) => (this.spans = Array.from(spans.values())),
        );
    }

    // TODO: update the relations store as well!
    mergeResources(
        _source: string | Resource,
        _target: string | Resource,
    ): void {
        const source = this.getResource(_source);
        const target = this.getResource(_target);

        this.update((body) => {
            if (source && source.label === target?.label)
                this.replaceResource(source, target);

            return body;
        });
    }

    getResource(res: string | Resource): Resource | undefined {
        return typeof res === "string" ? get(this.resources).get(res) : res;
    }

    removeAnnotation(id: string) {
        this.update((body) => {
            const span = body.querySelector(`#${CSS.escape(id)}`);
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

            return body;
        });
    }

    removeAnnotations(ids: string[] | Set<string>): void {
        ids.forEach(this.removeAnnotation);
    }

    removeResource(resourceID: string): void {
        this.update((body) => {
            const spans = this.spans.filter(
                (span) => span.getAttribute("resource") === resourceID,
            );

            this.removeAnnotations(spans.map((span) => span.id as string));

            return body;
        });
    }

    annotateRange(label: string, range: Range) {
        this.update((body) => {
            let span = newSpan(label, rangeToClass(range, "entity"));

            range.surroundContents(span);
            resources.storeEntitySpan(span) as Resource;
            //body.propagate(resource);

            spanWrappedButton(span) as HTMLButtonElement;

            return document.querySelector(".chunk-body") as Element;
        });
    }

    replaceResource(
        _source: string | Resource,
        _target: string | Resource,
    ): void {
        const source =
            typeof _source === "string" ? _source : _source.resourceid;
        const target =
            typeof _target === "string" ? _target : _target.resourceid;

        this.update((body) => {
            const spans = body.querySelectorAll(`span[resource="${source}"]`);

            spans.forEach((span) => span.setAttribute("resource", target));

            return body;
        });
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

        this.update((body) => {
            if (body) {
                const textNodes = getAllTextNodes(body);

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
            return body;
        });
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
