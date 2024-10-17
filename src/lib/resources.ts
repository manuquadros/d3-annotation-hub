import type { Readable, Unsubscriber } from "svelte/store";

export const strainLabel = "d3o:Strain";
export const enzymeLabel = "d3o:Enzyme";
export const bacteriaLabel = "d3o:Bacteria";

type ResourceMap = Map<string, Resource>;

export class Resource {
    resid: string;
    label: string = "";
    ids: Set<string> = new Set();
    spans: HTMLSpanElement[] = [];
    unsubscribe: Unsubscriber;

    constructor(resourceID: string, entspans: Readable<HTMLSpanElement[]>) {
        this.resid = resourceID;

        this.unsubscribe = entspans.subscribe((entspans) => {
            const spans = entspans.filter(
                (span) => span.getAttribute("resource") === resourceID,
            );

            this.spans = spans;

            if (!this.label && spans.length)
                this.label = spans[0].getAttribute("typeof") as string;

            spans.forEach((span) => this.ids.add(span.id as string));
        });
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
 * // - Existing resources are maintained for unchanged spans
 * // - Resources are cleaned up (unsubscribed) when their spans are removed
 */
export function resourceMap(
    entspans: Readable<HTMLSpanElement[]>,
): ResourceMap {
    const resources: ResourceMap = new Map();

    entspans.subscribe(($entspans) => {
        const resourceIDs = new Set(
            $entspans.map((span) => span.getAttribute("resource") as string),
        );

        Array.from(resources.keys()).forEach((key) => {
            if (!resourceIDs.has(key)) {
                resources.get(key)?.unsubscribe();
                resources.delete(key);
            }
        });

        resourceIDs.forEach((key) => {
            if (!resources.has(key)) {
                resources.set(key, new Resource(key, entspans));
            }
        });
    });

    return resources;
}

function nextResourceID(resources: ResourceMap): string {
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

// const labels = [enzymeLabel, strainLabel, bacteriaLabel];

// type labelToResources = Map<string, Array<string>>;

// export const classes: Readable<labelToResources> = derived(
//     resources,
//     ($resources) => {
//         const m = new Map();

//         labels.forEach((label) =>
//             m.set(
//                 label,
//                 Array.from($resources.keys()).filter(
//                     (key) => $resources.get(key)?.label === label,
//                 ),
//             ),
//         );

//         return m;
//     },
// );

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
