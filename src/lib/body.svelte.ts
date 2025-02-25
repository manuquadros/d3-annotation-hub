import { tick } from "svelte";
import { SvelteMap } from "svelte/reactivity";

import { isValidEntitySpan, newSpan, wrapRange, entID } from "$lib/utils.ts";
import { nextResourceID, type Resource } from "$lib/resources.svelte.ts";
import { RelationStore } from "$lib/relations.svelte.ts";
import { rangeToClass } from "$lib/ranges.ts";

import { Map, OrderedMap, Set, OrderedSet } from "immutable";

export class BodyStore {
    content: Element = $state(
        document.createDocumentFragment() as unknown as Element,
    );

    // TODO: entspans could be keyed by the resource id, actually, with values
    // corresponding to sets of span elements.
    entspans: SvelteMap<string, HTMLSpanElement> = $derived.by(() => {
        if (this.content) {
            let spans = Array.from(this.content.querySelectorAll("span"));
            spans = spans.filter((span) => isValidEntitySpan(span));
            const spanMap = new SvelteMap(spans.map((span) => [span.id, span]));
            return spanMap;
        } else {
            return new SvelteMap();
        }
    });

    resources: Map<string, Resource> = $derived.by(() => {
        const resMap = Map<string, Resource>();

        return resMap.withMutations((map) => {
            for (const span of this.entspans.values()) {
                const resourceid = span.getAttribute("resource") as string;
                const spanText = span.textContent || "";
                const resource = map.get(resourceid);

                if (!resource)
                    map.set(resourceid, {
                        resourceid,
                        name: span.textContent as string,
                        label: span.getAttribute("typeof") as string,
                    });
                else {
                    const name =
                        spanText.length > resource.name.length
                            ? spanText
                            : resource.name;
                    map.set(resourceid, { ...resource, name });
                }
            }
        });
    });

    relations = new RelationStore(() => this.resources);
    classes: Set<string> = $derived(
        Set(this.resources.toList().map((res) => res.label)),
    );
    nextResourceId: string = $derived(nextResourceID(this.resources));
    selectedSpan: HTMLSpanElement | null = null;

    constructor(chunk: Element) {
        // Initialize all entity spans, making sure they have an ID and a button.
        this.content = chunk;
        const spans = this.content.querySelectorAll("span");

        spans.forEach((span) => {
            span.id = String(entID());
        });
    }

    // TODO: update the relations store as well!
    mergeResources(
        _source: string | Resource,
        _target: string | Resource,
    ): void {
        const source =
            typeof _source === "string" ? this.getResource(_source) : _source;
        const target =
            typeof _target === "string" ? this.getResource(_target) : _target;

        if (source && source.label === target?.label)
            this.replaceResource(source, target);
    }

    getResource(resourceid: string): Resource | undefined {
        return this.resources.find((res) => res.resourceid === resourceid);
    }

    getResourceNames(resource: string | Resource): Set<string> {
        const resourceid =
            typeof resource === "string" ? resource : resource.resourceid;

        const names = Set<string>();

        this.entspans.values().forEach((el) => {
            if (el.getAttribute("resource") == resourceid)
                names.add(el.textContent as string);
        });

        return names;
    }

    removeAnnotation(id: string) {
        const tmp = this.content.cloneNode(true) as Element;
        const span = tmp.querySelector(`#${CSS.escape(id)}`);
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

        this.content = tmp;
    }

    removeAnnotations(ids: string[] | Set<string>): void {
        ids.forEach((id) => this.removeAnnotation(id));
    }

    /**
     * Remove f
     *
     * @param  -
     * @returns
     */
    removeResource(resource: string | HTMLElement): void {
        const resourceId =
            resource instanceof HTMLElement
                ? resource.getAttribute("resource")
                : resource;
        const spans = this.entspans
            .entries()
            .filter(([, span]) => span.getAttribute("resource") === resourceId);

        this.removeAnnotations(
            Array.from(spans.map(([spanId]) => spanId as string)),
        );
        this.relations.cleanup();
    }

    annotateRange(label: string, range: Range) {
        const resid = this.nextResourceId;
        const span = newSpan(
            label,
            rangeToClass(range, "entity"),
            this.nextResourceId,
        );

        range.surroundContents(span);

        queueMicrotask(async () => {
            const chunkBody = document.querySelector(".chunk-body") as Element;
            this.content = chunkBody.cloneNode(true) as Element;
            await this.propagate(this.getResource(resid) as Resource);
        });
    }

    replaceResource(source: Resource, target: Resource): void {
        // Update all the relations mentioning `source` to point to `target`
        this.relations.replaceEntity(source, target);

        // Update the reference of spans in the document to point to the
        // `target`.
        const content = this.content?.cloneNode(true) as Element;
        const spans = content?.querySelectorAll(
            `span[resource="${source.resourceid}"]`,
        );
        spans?.forEach((span) =>
            span.setAttribute("resource", target.resourceid),
        );
        this.content = content;
    }

    async propagate(resource: Resource): Promise<void> {
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

                for (const name of this.getResourceNames(resource)) {
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

            queueMicrotask(async () => {
                const chunkBody = document.querySelector(
                    ".chunk-body",
                ) as Element;
                this.content = chunkBody.cloneNode(true) as Element;
                await tick();
            });
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
