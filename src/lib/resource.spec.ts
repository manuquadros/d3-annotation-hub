import { expect, test } from "vitest";
import { Resource } from "$lib/resources.ts";

const doc = new DOMParser().parseFromString(
    '<span class="entity" resource="#T2" typeof="d3o:Bacteria", id="1">R. erythropolis</span><span class="entity" resource="#T2" typeof="d3o:Bacteria", id="2">R. erythropolis</span><span class="entity" resource="#T2" typeof="d3o:Bacteria", id="3">Rhodococcus erythropolis</span>',
    "text/html",
);

test("span is parsed into a Resource", () => {
    const spans = doc.querySelectorAll("span");
    const resource = new Resource(spans);

    expect(resource.name).not.toEqual("R. erythropolis");
    expect(resource.name).toEqual("Rhodococcus erythropolis");
});
