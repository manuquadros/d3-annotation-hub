import { writable } from "svelte/store";
import type { Resource } from "$lib/resources.ts";

interface Pair {
    subject: Resource;
    object: Resource;
}

const { subscribe, update } = writable(new Map());
export const relations = {
    subscribe,
    add: _addRelation,
};

function _addRelation(subj: Resource, predicate: string, obj: Resource): void {
    update((relations) => {
        const pair: Pair = {
            subject: subj,
            object: obj,
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
