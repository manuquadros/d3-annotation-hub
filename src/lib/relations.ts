import { writable } from "svelte/store";
import type { Readable, Subscriber } from "svelte/store";

import type { Resource } from "$lib/resources.ts";

export interface ResourcePair {
    subject: Resource;
    object: Resource;
}

export interface Triple {
    subject: Resource;
    predicate: string;
    object: Resource;
}

/**
 * Class of Svelte stores containing relations between Resources, indexed by
 * a predicate, corresponding to RDF triples.
 * The store keeps track of updates to the resource store, in order to remove
 * relations referring to resources that have been removed.
 */
export class RelationStore implements Readable<Set<Triple>> {
    vertices = new Set<Resource>();
    subscribe;
    update;

    /**
     * Generates the relation store and subscribes to the resource store.
     *
     * @constructor
     * @param {Readable<Map<string, Resource>>} Svelte resource store
     */
    constructor(resources: Readable<Map<string, Resource>>) {
        const { subscribe, update } = writable<Set<Triple>>(new Set());

        this.subscribe = subscribe;
        this.update = update;

        this.subscribe((relations) =>
            relations.forEach((triple) => {
                const { subject, object } = triple;
                this.vertices.add(subject);
                this.vertices.add(object);
            }),
        );

        resources.subscribe((resources) =>
            this.vertices.forEach((res) => {
                if (!resources.has(res.resid)) this.removeVertex(res);
            }),
        );
    }

    add(subject: Resource, predicate: string, object: Resource): void {
        this.update((relations) => {
            relations.add({ subject, predicate, object });
            return relations;
        });
    }

    remove(subject: Resource, predicate: string, object: Resource): void {
        this.update((relations) => {
            relations.delete({ subject, predicate, object });

            return relations;
        });
    }

    removeVertex(vertex: Resource): void {
        this.update((relations) => {
            relations.forEach((triple) => {
                if (triple.subject === vertex || triple.object === vertex)
                    relations.delete(triple);
            });
            return relations;
        });
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
