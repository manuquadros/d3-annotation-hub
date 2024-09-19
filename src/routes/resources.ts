import { writable, get } from "svelte/store";
import type { Writable } from "svelte/store";

interface Entity {
        [index: string]: string | number;
        name: string;
        count: number;
}

export const entities: Writable<Map<string, Map<string, Entity>>> =
        writable(new Map());

function entityCount(): number {
        return Array.from(get(entities).values())
                .map((resources) => resources.size)
                .reduce((x, y) => x + y);
}

export function getOrCreateResource(label: string, text: string): string {
        const existingResource: string | null = findResource(label, text);
        if (existingResource) {
                return existingResource;
        } else {
                return "#T" + (entityCount() + 1);
        }
}

export function removeEntity(label: string, resource: string) {
        entities.update((entities) => {
                let res = entities.get(label)?.get(resource);
                if (res) {
                        res.count -= 1;
                        if (res.count < 1) {
                                entities.get(label)?.delete(resource);
                        }
                }
                return entities;
        });
}

export function removeEntitySpan(span: HTMLSpanElement): void {
        const label = span.getAttribute("typeof");
        const resource = span.getAttribute("resource");
        if (label && resource) {
                removeEntity(label, resource);
        } else {
                console.log(span, "Malformed span");
        }
}

export function storeEntity(label: string, resource: string, text: string) {
        entities.update((entities) => {
                let resources = entities.get(label);
                if (resources) {
                        let res = resources.get(resource);
                        if (res) {
                                res.count += 1;
                                if (text.length > res.name.length) {
                                        res.name = text;
                                }
                        } else {
                                resources.set(resource, { name: text, count: 1 });
                        }
                } else {
                        entities.set(
                                label,
                                new Map([[resource, { name: text, count: 1 }]]),
                        );
                }
                return entities;
        });
}

export function storeEntitySpan(span: Element): void {
        const label = span.getAttribute("typeof") as string;
        const text = span.textContent;

        if (!span.getAttribute("resource")) {
                span.setAttribute(
                        "resource",
                        getOrCreateResource(label, text as string),
                );
        }
        const resource = span.getAttribute("resource")

        if (label !== "d3o:OOS" && label !== "OOS") {
                if (label && resource && text) {
                        storeEntity(label, resource, text);
                } else {
                        console.log("Malformed span");
                }
        }
}

export function findResource(label: string, text: string): string | null {
        const resources = get(entities).get(label);
        if (resources) {
                for (const [key, res] of resources) {
                        if (res.name === text) {
                                return key;
                        }
                }
        }
        return null;
}
