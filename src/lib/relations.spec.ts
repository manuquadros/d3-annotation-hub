import { describe, expect, test } from "vitest";
import { get } from "svelte/store";
import { bodyStore } from "$lib/body.ts";

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

    return new bodyStore(content);
}

describe("relations", () => {
    const body = setup();

    let size: number;
    let otherSize: number;

    const t3 = get(body.resources).get("#T3");
    const t7 = get(body.resources).get("#T7");

    body.relations.subscribe((relations) => (size = relations.size));

    body.relations.add(t3, "strainOf", t7);

    test("relations store works", () => {
        expect(size).toBe(1);
    });
});
