import { writable, get } from "svelte/store";
import type { Readable } from "svelte/store";

import type { Resource } from "$lib/resources.svelte.ts";
import { SvelteSet } from "svelte/reactivity";

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
    #resources: Map<string, Resource> | undefined = $state();

    vertices: Set<Resource> = $derived.by(() => {
        if (this.#resources)
            return new Set(Array.from(this.#resources.values()));
        else return new Set();
    });

    /**
     * Generates the relation store and subscribes to the resource store.
     *
     * @constructor
     * @param {Readable<Map<string, Resource>>} resources - Svelte resource store
     */
    constructor(resources: Map<string, Resource>) {
        super();
        this.#resources = resources;
    }

    cleanup() {
        this.forEach(({ subject, predicate, object }) => {
            if (!this.vertices.has(subject) || !this.vertices.has(object)) {
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
