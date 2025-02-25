import { describe, expect, test } from "vitest";
import { get } from "svelte/store";
import { BodyStore } from "$lib/body.svelte.ts";
import type { Resource } from "./resources.svelte.ts";

const chunk = `<annotation>
  <div class="metadata">
    <p>Excerpt from:
      <strong><italic>Rhodococcus erythropolis</italic> ATCC 25544 as a suitable source of cholesterol oxidase: cell-linked and extracellular enzyme synthesis, purification and concentration</strong></p>
    <p>Authors: <name>
            <surname>Sojo, </surname>
            Mar M
           - </name><name>
            <surname>Bru, </surname>
            Roque R
           - </name><name>
            <surname>García-Carmona, </surname>
            Francisco F
          </name></p>
    <p>DOI: 10.1186/1472-6750-2-3</p>
  </div>
  <div class="chunk-body" prefix="d3o: https://purl.dsmz.de/schema/"><p>In a previous work [<xref ref-type="bibr" rid="B9">9</xref>] we described the cell-bound and extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span> activities from <italic><span class="entity" resource="#T2" typeof="d3o:Bacteria">R. erythropolis</span></italic> <span class="entity" resource="#T3" typeof="d3o:Strain">ATCC 25544</span>, achieving in optimal conditions 55% cell-bound and 45% extracellular activity. Their enzymatic properties strongly supported the idea that the particulate and the extracellular cholesterol oxidases are two different forms of the same enzyme with an estimated molecular mass of 55 kDa. In this work we optimize the culture conditions in a 2-liter fermentor of this extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span> producer strain and carry out the extraction, partial purification and concentration of both types of <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span> by using Triton X-114 phase separation. The results obtained are very promising for the use of this strain and this technique in the industrial processing of <span class="entity" resource="#T7" typeof="OOS">bacteria</span> to obtain <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span>.</p></div>
</annotation>`;

function setup() {
    const content = new DOMParser().parseFromString(chunk, "text/html");

    return new BodyStore(content.querySelector(".chunk-body") as Element);
}

describe("relations", () => {
    const body = setup();
    const relations = body.relations;

    const t1 = body.getResource("#T1") as Resource;
    const t2 = body.getResource("#T2") as Resource;
    const t3 = body.getResource("#T3") as Resource;

    const t3t2 = {
        subject: t3,
        predicate: "d3o:hasSpecies",
        object: t2,
    };

    body.relations.add(t3t2);

    test("relations store works", () => {
        expect(relations.size).toBe(1);
    });

    test("relations are added correctly", () => {
        body.relations.add({
            subject: t3,
            predicate: "d3o:hasEnzyme",
            object: t1,
        });

        expect(relations.size).toBe(2);
    });

    test("remove object updates relations", () => {
        body.removeResource("#T2");
        expect(relations.size).toBe(1);
        expect(body.relations.predicates).not.toContain("d3o:hasSpecies");
    });
});
