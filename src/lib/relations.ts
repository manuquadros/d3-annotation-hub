import { writable, get } from "svelte/store";
import type { Readable } from "svelte/store";

import type { Resource } from "$lib/resources.ts";

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

/**
 * Class of Svelte stores containing relations between Resources, indexed by
 * a predicate, corresponding to RDF triples.
 * The store keeps track of updates to the resource store, in order to remove
 * relations referring to resources that have been removed.
 */
export class RelationStore implements Readable<Set<Triple>> {
    vertices = new Set<Resource>();
    predicates = new Set<string>();
    subscribe;
    update;

    /**
     * Generates the relation store and subscribes to the resource store.
     *
     * @constructor
     * @param {Readable<Map<string, Resource>>} resources - Svelte resource store
     */
    constructor(resources: Readable<Map<string, Resource>>) {
        const { subscribe, update } = writable<Set<Triple>>(new Set());

        this.subscribe = subscribe;
        this.update = update;

        this.subscribe((relations) => {
            relations.forEach((triple) => {
                const { subject, object } = triple;
                this.vertices.add(subject);
                this.vertices.add(object);
            });

            this.predicates = new Set(
                relations[Symbol.iterator]().map((triple) => triple.predicate),
            );
        });

        resources.subscribe((resources) =>
            this.vertices.forEach((res) => {
                if (!resources.has(res.resid)) this.removeVertex(res);
            }),
        );
    }

    add(triple: Triple): void {
        this.update((relations) => {
            relations.add(triple);
            return relations;
        });
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

        this.update((relations) => {
            if (subject && predicate && object) {
                relations.delete({ subject, predicate, object });
            } else {
                this.subset(query).forEach((triple) =>
                    relations.delete(triple),
                );
            }

            return relations;
        });
    }

    subset(query: TripleQuery): Set<Triple> {
        const constraints = Object.keys(query).filter(Boolean);
        const values = new Set<Triple>();

        get(this).forEach((triple) => {
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
