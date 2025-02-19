import { SvelteMap } from "svelte/reactivity";
import { derived } from "svelte/store";
import type { Readable, Unsubscriber } from "svelte/store";

export const strainLabel = "d3o:Strain";
export const enzymeLabel = "d3o:Enzyme";
export const bacteriaLabel = "d3o:Bacteria";

export class Resource {
    resourceid: string = "";
    label: string = "";
    spans = new Set<HTMLSpanElement>();

    add(span: HTMLSpanElement) {
        const resid = span.getAttribute("resource");
        const label = span.getAttribute("typeof");

        if (resid && label) {
            if (
                this.resourceid &&
                this.label &&
                (resid !== this.resourceid || label !== this.label)
            ) {
                throw new Error("Trying to add a span to the wrong resource");
            }

            this.resourceid = resid;
            this.label = label;
            this.spans.add(span);
        }

        return this;
    }

    extend(spans: HTMLSpanElement[] | NodeListOf<HTMLSpanElement>) {
        spans.forEach((span) => this.add(span));

        return this;
    }

    get spanids(): Set<string> {
        return new Set(Array.from(this.spans.values()).map((span) => span.id));
    }

    /**
     * Get the resource's display name
     *
     * @returns The longest string among the contents of the spans corresponding
     * to the resource.
     */
    get name(): string {
        let curr = "";

        for (const str of this.names) {
            curr = str.length > curr.length ? str : curr;
        }

        return curr;
    }

    get names(): Set<string> {
        const _names = new Set<string>();

        for (const span of this.spans) {
            const text = span.textContent;

            if (text) _names.add(text);
        }

        return _names;
    }
}

/**
 * Creates and maintains a map of resources based on a store of span elements.
 * Each span must have a "resource" attribute serving as the resource identifier.
 * The returned map is automatically updated when the input span array changes.
 *
 * @param {Readable<HTMLSpanElement[]>} entspans - A Svelte readable store
 *   containing an array of span elements
 * @returns {Map<string, Resource>} A map where:
 *   - Keys are resource IDs extracted from span "resource" attributes
 *   - Values are Resource instances that maintain subscriptions to
 *       their corresponding spans
 *
 * // The resources map will automatically update when spans change:
 * // - New resources are created for new span elements
 * // - Resources are cleaned up when their spans are removed
 */
export function resourceStore(
    entspans: SvelteMap<string, HTMLSpanElement>,
): SvelteMap<string, Resource> {
    const resources = new SvelteMap<string, Resource>();

    for (const span of entspans.values()) {
        const resourceid = span.getAttribute("resource") as string;

        const res: Resource =
            resources.get(resourceid) ||
            (resources
                .set(resourceid, new Resource())
                .get(resourceid) as Resource);

        res.add(span);
    }

    return resources;
}

export function nextResourceID(resources: Map<string, Resource>): string {
    const keys = Array.from(resources.keys()).toSorted(
        (a, b) => Number(a.slice(2)) - Number(b.slice(2)),
    );

    if (keys.length) {
        const lastKeyNumber = Number(keys.at(-1)?.slice(2));

        return "#T" + String(lastKeyNumber + 1);
    } else {
        return "#T1";
    }
}

export function sameClass(a: Resource, b: Resource): boolean {
    return a.label === b.label;
}
export function isStrain(a: Resource): boolean {
    return a.label === strainLabel;
}
export function isBacteria(a: Resource): boolean {
    return a.label === bacteriaLabel;
}
export function isEnzyme(a: Resource): boolean {
    return a.label === enzymeLabel;
}
export function isOrganism(a: Resource): boolean {
    return isBacteria(a) || isStrain(a);
}

function getOrCreateResourceID(
    resources: Map<string, Resource>,
    name: string,
): string {
    const existingResource: string | null = _findResource(resources, name);

    return existingResource ? existingResource : nextResourceID(resources);
}

function _findResource(
    resources: Map<string, Resource>,
    name: string,
): string | null {
    for (const [key, res] of resources) {
        if (res.names.has(name)) {
            return key;
        }
    }
    return null;
}
