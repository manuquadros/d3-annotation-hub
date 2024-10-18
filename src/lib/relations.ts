import { writable } from "svelte/store";
import type { Readable } from "svelte/store";

import type { Resource } from "$lib/resources.ts";

export interface ResourcePair {
    subject: Resource;
    object: Resource;
}

export interface Triple {
    subject: Resource;
    predicate: Resource;
    object: Resource;
}

/**
 * Class of Svelte stores containing relations between Resources, indexed by
 * a predicate, corresponding to RDF triples.
 * The store keeps track of updates to the resource store, in order to remove
 * relations referring to resources that have been removed.
 */
export class relationStore {
    vertices = new Set<Resource>();

    /**
     * Generates the relation store and subscribes to the resource store.
     *
     * @constructor
     * @param {Readable<Map<string, Resource>>} Svelte resource store
     */
    constructor(resources: Readable<Map<string, Resource>>) {
        const { subscribe, set, update } = writable<Set<Triple>>(new Set());

        this.subscribe = subscribe;
        this.update = update;

        this.subscribe((relations) =>
            relations.forEach((triple) => {
                const { subj, obj } = triple;
                this.vertices.add(subj);
                this.vertices.add(obj);
            }),
        );

        resources.subscribe((resources) =>
            this.vertices.forEach((res) => {
                if (!resources.has(res.resid)) this.removeVertex(res);
            }),
        );
    }

    add(subject: Resource, predicate: string, object: Resource): void {
        this.update((relations) =>
            relations.add({ subject, predicate, object }),
        );
    }

    remove(subject: Resource, predicate: string, object: Resource): void {
        this.update((relations) =>
            relations.delete({ subject, predicate, object }),
        );
    }

    removeVertex(vertex: Resource): void {
        this.update((relations) =>
            relations.forEach((triple) => {
                if (triple.subject === vertex || triple.object === vertex)
                    relations.delete(triple);
            }),
        );
    }
}

export function displayPredicate(predicate: string): string {
    switch (predicate) {
        case "d3o:hasSpecies":
            return "is a strain of";
        case "d3o:hasEnzyme":
            return "has enzyme";
    }
}
