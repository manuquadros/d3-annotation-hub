import type { OrderedMap, Set } from "immutable";

export const strainLabel = "d3o:Strain";
export const enzymeLabel = "d3o:Enzyme";
export const bacteriaLabel = "d3o:Bacteria";

export type ResourceId = string;
export type Label = string;
export type Resource = {
    resourceid: string;
    name: string;
    label: string;

    // /**
    //  * Get the resource's display name
    //  *
    //  * @returns The longest string among the contents of the spans corresponding
    //  * to the resource.
    //  */
    // get name(): string {
    //     let curr = "";

    //     for (const str of this.names) {
    //         curr = str.length > curr.length ? str : curr;
    //     }

    //     return curr;
    // }

    // get names(): Set<string> {
    //     const _names = new Set<string>();

    //     for (const span of this.spans) {
    //         const text = span.textContent;

    //         if (text) _names.add(text);
    //     }

    //     return _names;
    // }
};
export type ResourceMap = OrderedMap<ResourceId, Resource>;

export function nextResourceID(resources: Set<Resource>): string {
    const last: ResourceId | undefined = resources.maxBy(
        (res) => res.resourceid,
    )?.resourceid;

    if (last) {
        const lastIDNumber = Number(last.slice(2));

        return "#T" + String(lastIDNumber + 1);
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
