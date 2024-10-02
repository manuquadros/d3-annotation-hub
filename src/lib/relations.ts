import { writable, get } from "svelte/store";
import type { Writable } from "svelte/store";

import { resources } from "$lib/resources.ts";
import type { Resource } from "$lib/resources.ts";

interface Pair {
    subject: Resource;
    object: Resource;
}

const { subscribe, update } = writable(new Map());
export const relations: Writable<Map<string, Set<Pair>>> = {
    subscribe,
    add: _addRelation,
};

function _addRelation(subj: Resource, predicate: string, obj: Resource): void {
    update((relations) => {
        const pair: Pair = {
            subject: get(resources).get(subj),
            object: get(resources).get(obj),
        };
        const rel = relations.get(predicate);

        if (rel) {
            rel.add(pair);
        } else {
            relations.set(predicate, new Set([pair]));
        }
        return relations;
    });
}

export function displayPredicate(predicate: string): string {
    switch (predicate) {
        case "d3o:hasSpecies":
            return "is a strain of";
        case "d3o:hasEnzyme":
            return "has enzyme";
    }
}
