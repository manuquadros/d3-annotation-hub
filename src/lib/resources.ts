import { writable, get, derived } from "svelte/store";
import type { Writable, Readable } from "svelte/store";

export const strainLabel = "d3o:Strain";
export const enzymeLabel = "d3o:Enzyme";
export const bacteriaLabel = "d3o:Bacteria";

import { body, entitySpans } from "$lib/body.ts";
import { entID } from "$lib/utils.ts";

const { subscribe, set, update } = writable(new Map()) as Writable<
    Map<string, Resource>
>;

type PairIdResource = {
    id: string;
    resource: Resource;
};

export const resources = {
    subscribe,
    storeEntitySpan: _storeEntitySpan,
    storeEntity: _storeEntity,
    removeEntity: _removeEntity,
    removeEntitySpan: _removeEntitySpan,
    find: _findResource,
    merge: _mergeResources,
    reset: () => set(new Map()),

    querySpan(span: HTMLSpanElement): PairIdResource | null {
        const rid = span.getAttribute("resource");
        const res = rid ? get(resources).get(rid) : null;

        return rid && res ? { id: rid, resource: res } : null;
    },

    hasResource(res: HTMLSpanElement | string): boolean {
        if (res instanceof HTMLSpanElement && res.hasAttribute("resource")) {
            return get(resources).has(res.getAttribute("resource") as string);
        } else {
            return get(resources).has(res as string);
        }
    },
};

const nextResourceID = derived(resources, ($resources) =>
    incrementLastKey(Array.from($resources.keys())),
);

function incrementLastKey(arr: Array<string>): string {
    const nextNumber = 1 + Number(arr.at(-1).slice(2));
    return "#T" + String(nextNumber);
}

export class Resource {
    label: string;
    ids: Set<string> = new Set([]);
    spans: HTMLSpanElement[] = [];

    constructor(label: string, id: string) {
        this.label = label;
        this.ids.add(id);

        entitySpans.subscribe(
            (spans) =>
                (this.spans = spans.filter((span) => this.ids.has(span.id))),
        );
    }

    /**
     * Get the resource's display name
     *
     * @returns The longest string among the contents of the spans corresponding
     * to the resource.
     */
    get name(): string {
        let curr = "";

        for (const span of this.spans) {
            const text = span.textContent;
            if (text && text.length > curr.length) {
                curr = text;
            }
        }

        return curr;
    }
}

const labels = [enzymeLabel, strainLabel, bacteriaLabel];

type labelToResources = Map<string, Array<string>>;

export const classes: Readable<labelToResources> = derived(
    resources,
    ($resources) => {
        const m = new Map();

        labels.forEach((label) =>
            m.set(
                label,
                Array.from($resources.keys()).filter(
                    (key) => $resources.get(key)?.label === label,
                ),
            ),
        );

        return m;
    },
);

function labelOf(resource: string | Resource): string {
    if (typeof resource === "string") {
        resource = get(resources).get(resource);
    }

    return resource.label;
}

export function sameClass(a: string, b: String): boolean {
    return labelOf(a) === labelOf(b);
}
export function isStrain(a: string): boolean {
    return labelOf(a) === strainLabel;
}
export function isBacteria(a: string): boolean {
    return labelOf(a) === bacteriaLabel;
}
export function isEnzyme(a: string): boolean {
    return labelOf(a) === enzymeLabel;
}
export function isOrganism(a: string): boolean {
    return isBacteria(a) || isStrain(a);
}

export function _removeEntity(key: string) {
    update((resources) => {
        //body.removeAnnotations();
        resources.delete(key);
        return resources;
    });
}

export function _removeEntitySpan(span: HTMLSpanElement): void {
    const result = resources.querySpan(span);

    if (result) {
        body.removeAnnotations(result.resource.ids);
        resources.removeEntity(result.id);
    } else {
        console.log(span, "Malformed span");
    }
}

function _storeEntity(
    label: string,
    resourceId: string,
    id: string,
): Resource | undefined {
    let res: Resource | undefined;

    update((resources) => {
        res = resources.get(resourceId);

        if (res) {
            res.ids.add(id);
        } else {
            res = new Resource(label, id);
            resources.set(resourceId, res);
        }

        return resources;
    });

    return res;
}

/**
 * Stores the entity described by an HTMLSpanElement into the resources store. If a
 * corresponding resource already exists, the span id is added to the set of ids
 * contained by that resource. Otherwise, a new resource is created
 *
 * @param span
 * @returns The resource described by the span
 */
function _storeEntitySpan(span: HTMLSpanElement): Resource | undefined {
    let res: Resource | undefined;

    update((resources) => {
        const label = span.getAttribute("typeof");
        const text = span.textContent;

        if (label && text) {
            let resourceId = span.getAttribute("resource");

            if (!resourceId) {
                resourceId = getOrCreateResource(label, text);
                span.setAttribute("resource", resourceId);
            }

            if (!span.id) {
                span.id = String(entID());
            }

            res = _storeEntity(label, resourceId, span.id);
        } else {
            console.log("Malformed span: ", span.outerHTML);
        }

        return resources;
    });

    return res;
}

function getOrCreateResource(label: string, name: string): string {
    const existingResource: string | null = _findResource(name);
    if (existingResource) {
        return existingResource;
    } else {
        return get(nextResourceID);
    }
}

function _findResource(name: string): string | null {
    for (const [id, res] of get(resources)) {
        if (res.names.includes(name)) {
            return id;
        }
    }
    return null;
}

export function _mergeResources(source: string, target: string): void {
    update((resources) => {
        const resSource = resources.get(source);
        const resTarget = resources.get(target);

        if (resSource && resSource.label === resTarget?.label) {
            resSource.ids.forEach((id) => resTarget.ids.add(id));
            resources.delete(source);
            body.replaceResource(source, target);
        }

        return resources;
    });
}
