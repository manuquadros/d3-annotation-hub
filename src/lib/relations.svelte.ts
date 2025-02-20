import { writable, get } from "svelte/store";
import type { Readable } from "svelte/store";

import type { Resource } from "$lib/resources.svelte.ts";
import { SvelteMap, SvelteSet } from "svelte/reactivity";
import { OrderedSet } from "immutable";

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
    #resources: OrderedSet<Resource> = $state(OrderedSet());

    /**
     * Generates the relation store and subscribes to the resource store.
     *
     * @constructor
     * @param {Readable<Map<string, Resource>>} resources - Svelte resource store
     */
    constructor(resources: OrderedSet<Resource>) {
        super();
        this.#resources = resources;
    }

    // TODO: write tsdoc
    cleanup() {
        this.forEach(({ subject, predicate, object }) => {
            if (!this.#resources.has(subject) || !this.#resources.has(object)) {
                this.delete({ subject, predicate, object });
            }
        });
    }

    get predicates(): SvelteSet<string> {
        const preds = new SvelteSet<string>();
        this.forEach((t) => preds.add(t.predicate));
        return preds;
    }

    /**
     * Remove from the store all triples matching the query. If the query consists
     * of a complete triple, with subject, predicate, and object, remove that triple
     * from the store. If it only contains one or two of those elements,
     * remove from the store all triples satisfying all of the given constraints.
     *
     * @param query -
     * @returns -
     */
    remove(query: TripleQuery): void {
        const { subject, predicate, object } = query;

        if (subject && predicate && object) {
            this.delete({ subject, predicate, object });
        } else {
            this.subset(query).forEach((triple) => this.delete(triple));
        }
    }

    subset(query: TripleQuery): Set<Triple> {
        const constraints = Object.keys(query).filter(Boolean);
        const values = new Set<Triple>();

        this.forEach((triple) => {
            if (constraints.every((c) => triple[c] === query[c]))
                values.add(triple);
        });

        return values;
    }

    /**
     * Update all triples pointing to `source` so that they point to `target`.
     *
     * @param source - Resource to be replaced.
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
