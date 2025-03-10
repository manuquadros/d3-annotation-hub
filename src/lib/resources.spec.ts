import { expect, test } from "vitest";
import { BodyStore } from "./body.svelte";

const doc = new DOMParser().parseFromString(
    '<span class="entity" resource="#T2" typeof="d3o:Bacteria" id="1">R. erythropolis</span><span class="entity" resource="#T2" typeof="d3o:Bacteria" id="2">R. erythropolis</span><span class="entity" resource="#T2" typeof="d3o:Bacteria" id="3"><button class="entity" resource="#T2" typeof="d3o:Bacteria" type="button">Rhodococcus erythropolis</button></span>',
    "text/html",
);

test("span is parsed into a Resource", () => {
    const body = new BodyStore(doc.documentElement);

    expect(body.resources.first()?.name).not.toEqual("R. erythropolis");
    expect(body.resources.first()?.name).toEqual("Rhodococcus erythropolis");
});
