import type { Resource } from "$lib/resources.svelte.ts";
import { SvelteSet } from "svelte/reactivity";
import { Set, Map } from "immutable";

export interface ResourcePair {
    subject: Resource;
    object: Resource;
}

export type Triple = {
    [index: string]: Resource | string;
    subject: Resource;
    predicate: string;
    object: Resource;
};

export type TripleQuery = {
    [index: string]: Resource | string | undefined;
    subject?: Resource;
    predicate?: string;
    object?: Resource;
};

export class RelationStore extends SvelteSet<Triple> {
    #getResources: () => Map<string, Resource> = $state(() =>
        Map<string, Resource>(),
    );
    #resources = $derived(this.#getResources());

    /**
     * Generates the relation store and subscribes to the resource store.
     *
     * @param resources - Svelte resource store
     */
    constructor(resourcesGetter: () => Map<string, Resource>) {
        super();
        this.#getResources = resourcesGetter;
    }

    /**
     * Removes any triples from the store where either the subject or object
     * resource no longer exists in the resources set.
     *
     */
    cleanup() {
        this.values()
            .filter(
                ({ subject, object }) =>
                    !this.#resources.has(subject.resourceid) ||
                    !this.#resources.has(object.resourceid),
            )
            .forEach((res) => this.delete(res));
    }

    get predicates(): Set<string> {
        return Set(this.values().map((t) => t.predicate));
    }

    /**
     * Remove from the store all triples matching the query. If the query consists
     * of a complete triple, with subject, predicate, and object, remove that triple
     * from the store. If it only contains one or two of those elements,
     * remove from the store all triples satisfying all of the given constraints.
     *
     * @param query - Specification of the terms a triple must contain to be removed.
     */
    remove(query: TripleQuery): void {
        const { subject, predicate, object } = query;

        if (subject && predicate && object) {
            this.delete({ subject, predicate, object });
        } else {
            console.debug(this);

            const sub = this.subset(query);
            console.debug(sub);
            sub.forEach((triple) => this.delete(triple));
        }
    }

    /**
     * Return all the triples in the store that match the query. If the query consists
     * of a complete triple, with subject, predicate, and object, return that triple
     * from the store. If it only contains one or two of those elements,
     * return all the triples satisfying all of the given constraints.
     *
     * @param query - Specification of the terms a triple must contain to be in the
     *                return set.
     * @returns The set of triples matching the query
     */
    subset(query: TripleQuery): Set<Triple> {
        const constraints = Object.keys(query).filter(Boolean);

        return Set(
            this[Symbol.iterator]().filter((triple) => {
                for (const c of constraints) {
                    let a: string | Resource = triple[c];
                    let b: string | Resource | undefined = query[c];

                    if (b) {
                        if (typeof a !== "string") a = a.resourceid;
                        if (typeof b !== "string") b = b.resourceid;

                        if (a !== b) return false;
                    }
                }

                return true;
            }),
        );
    }

    /**
     * Update all triples pointing to `source` so that they point to `target`.
     *
     * @param source - Resource to be replaced
     * @param target - Resource to replace `source`.
     */
    replaceEntity(source: Resource, target: Resource) {
        this.forEach((triple) => {
            if (triple.subject === source) {
                this.delete(triple);
                this.add({ ...triple, subject: target });
            }
            if (triple.object === source) {
                this.delete(triple);
                this.add({ ...triple, object: target });
            }
        });
    }
}

/**
 * Return an appropriate string representation for `predicate`.
 *
 * @param predicate - RDF predicate to be displayed.
 * @returns String representation of `predicate`, if available.
 */
export function displayPredicate(predicate: string): string | undefined {
    switch (predicate) {
        case "d3o:hasSpecies":
            return "is a strain of";
        case "d3o:hasEnzyme":
            return "has enzyme";
    }
}

export function triple(
    subject: Resource,
    predicate: string,
    object: Resource,
): Triple {
    return { subject, predicate, object };
}
