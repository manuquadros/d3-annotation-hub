import { writable, get, derived } from "svelte/store";
import type { Writable } from "svelte/store";

export const strainLabel = "d3o:Strain";
export const enzymeLabel = "d3o:Enzyme";
export const bacteriaLabel = "d3o:Bacteria";

const { subscribe, set, update } = writable(new Map()) as Writable<
    Map<string, Resource>
>;

export const resources = {
    subscribe,
    storeEntitySpan: _storeEntitySpan,
    storeEntity: _storeEntity,
    removeEntity: _removeEntity,
    removeEntitySpan: _removeEntitySpan,
    find: _findResource,
    merge: _mergeResources,
    reset: () => set(new Map()),
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
    count: number;
    names: Array<string> = [];

    constructor(label: string, text: string): void {
        this.label = label;
        this.count = 1;
        this.addName(text);
    }

    addName(term: string) {
        if (!this.names.includes(term)) {
            if (term.length > this.name.length) {
                this.names.unshift(term);
            } else {
                this.names.push(term);
            }
        }
    }

    get name(): string {
        if (this.names.length) {
            return this.names[0];
        } else {
            return "";
        }
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
                    (key) => $resources.get(key).label === label,
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

export function _removeEntity(id: string) {
    update((resources) => {
        resources.delete(id);
        return resources;
    });
}

export function _removeEntitySpan(span: HTMLSpanElement): void {
    const resource = span.getAttribute("resource");
    if (resource) {
        resources.removeEntity(resource);
    } else {
        console.log(span, "Malformed span");
    }
}

function _storeEntity(label: string, resourceId: string, text: string) {
    update((resources) => {
        let res = resources.get(resourceId);

        if (res) {
            res.count += 1;
            res.addName(text);
        } else {
            resources.set(resourceId, new Resource(label, text));
        }

        return resources;
    });
}

function _storeEntitySpan(span: Element): void {
    update((resources) => {
        const label = span.getAttribute("typeof");
        const text = span.textContent;

        if (label && text) {
            let resourceId = span.getAttribute("resource");
            if (!resourceId) {
                resourceId = getOrCreateResource(label, text);
                span.setAttribute("resource", resourceId);
            }
            _storeEntity(label, resourceId, text);
        } else {
            console.log("Malformed span");
        }
        return resources;
    });
}

function getOrCreateResource(label: string, name: string): string {
    const existingResource: string | null = _findResource(name);
    if (existingResource) {
        return existingResource;
    } else {
        console.log(get(nextResourceID));
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

        if (resSource.label === resTarget.label) {
            resTarget.count += resSource.count;
            resSource.names.forEach((name) => resTarget.addName(name));
            resources.delete(source);
        }

        return resources;
    });
}
