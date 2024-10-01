import { render, screen, cleanup } from "@testing-library/svelte";
import { get } from "svelte/store";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import Summary from "$lib/components/Summary.svelte";
import ChunkBody from "$lib/components/ChunkBody.svelte";
import { resources, strainLabel, classes, labels } from "$lib/resources.ts";
import { dragAndDrop } from "$lib/test_utils.ts";
import { body } from "$lib/body.ts";

const chunk3 = `<annotation>
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
  <div class="chunk-body" prefix="d3o: https://purl.dsmz.de/schema/"><p>In a previous work [<xref ref-type="bibr" rid="B9">9</xref>] we described the cell-bound and extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span> activities from <italic><span class="entity" resource="#T2" typeof="d3o:Bacteria">R. erythropolis</span></italic> <span class="entity" resource="#T3" typeof="d3o:Strain">ATCC</span> <span class="entity" resource="#T4" typeof="d3o:Strain">25544</span>, achieving in optimal conditions 55% cell-bound and 45% extracellular activity. Their enzymatic properties strongly supported the idea that the particulate and the extracellular cholesterol oxidases are two different forms of the same enzyme with an estimated molecular mass of 55 kDa. In this work we optimize the culture conditions in a 2-liter fermentor of this extracellular <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span> producer strain and carry out the extraction, partial purification and concentration of both types of <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span> by using Triton X-114 phase separation. The results obtained are very promising for the use of this strain and this technique in the industrial processing of <span class="entity" resource="#T7" typeof="OOS">bacteria</span> to obtain <span class="entity" resource="#T1" typeof="d3o:Enzyme">cholesterol oxidase</span>.</p>                 <h3>Results and discussion</h3>                <h4>Batch cultivation of <span class="entity" resource="#T2" typeof="d3o:Bacteria">R. erythropolis</span> (<span class="entity" resource="#T10" typeof="d3o:Strain">ATCC 25544</span>)</h4>         <p>The <span class="entity" resource="#T7" typeof="OOS">bacteria</span> were grown on the GYS medium in a 2-liter scale fermentor in batch mode operation under pH and temperature controlled conditions. Under this conditions the cell yield was doubled (9.5 mg/ml vs. 4.8 mg/ml dry cell weight) and the cultivation time was reduced to one third (60 vs. 180 hours) as compared with shaken flasks. These results are in good agreement with the literature [<xref ref-type="bibr" rid="B12">12</xref>]. We found that addition of 2 g/l cholesterol to the culture broth [<xref ref-type="bibr" rid="B12">12</xref>], prepared as an aqueous <span class="entity" resource="#T12" typeof="d3o:Enzyme">emulsion</span> with the aid of Tween 80 at a weight ratio 2:1 results in a high yield of COX production [<xref ref-type="bibr" rid="B9">9</xref>], but the preparation procedure of that <span class="entity" resource="#T12" typeof="d3o:Enzyme">emulsion</span> had a marked influence in the final enzyme yield, although not on the cell weight, as seen in Table <xref ref-type="table" rid="T1">1</xref>. The spray-dry method resulted advantageous because the cholesterol :Tween 80 <span class="entity" resource="#T12" typeof="d3o:Enzyme">emulsion</span> formed readily and COX production increased in overall by three times with respect to the preparation of the cholesterol:Tween 80 mixture at the flame. Enzyme production improvement resulted larger as cell-linked (3.8-fold) than as extracellular (2.3-fold). This overall increase of COX production can be due to a better availability of cholesterol to the cell since particle size obtained by spray-dry is smaller.</p>         <table-wrap position="float" id="T1">           <label>Table 1</label>           <caption>             <p>Effect of the cholesterol emuIsification method on the production of COX.</p>           </caption>           <table frame="hsides" rules="groups">             <thead>               <tr>                 <td/>                 <td align="center" colspan="2">                   <bold>COX activity (U/ml)<sup>*</sup></bold>                 </td>                 <td/>               </tr>             </thead>             <tbody>               <tr>                 <td align="center">                   <bold>Emulsification cholesterol method</bold>                 </td>                 <td align="center">                   <bold>Cell-linked</bold>                 </td>                 <td align="center">                   <bold>extracellular</bold>                 </td>                 <td align="center">                   <bold>Dry weight (mg/ml)</bold>                 </td>               </tr>               <tr>                 <td colspan="4">                   <hr/>                 </td>               </tr>               <tr>                 <td align="center">Spray-dry</td>                 <td align="center">230</td>                 <td align="center">140</td>                 <td align="center">8.75</td>               </tr>               <tr>                 <td align="center">At the flame</td>                 <td align="center">60</td>                 <td align="center">60</td>                 <td align="center">9.05</td>               </tr>               <tr>                 <td align="center">Improvement</td>                 <td align="center">3.8</td>                 <td align="center">2.3</td>                 <td align="center">0.97</td>               </tr>             </tbody>           </table>           <table-wrap-foot>             <p><sup>*</sup>Enzymatic activity figures correspond to 70 hours of fermentation.</p></table-wrap-foot></table-wrap></div>
</annotation>`;

function setup() {
    const user = userEvent.setup();
    resources.reset();

    const chunkBodyContainer = document.createElement("div");
    const summaryContainer = document.createElement("div");

    const content = new DOMParser().parseFromString(chunk3, "text/html");
    body.set(content.querySelector(".chunk-body"));

    const chunkBody = render(ChunkBody, {
        target: chunkBodyContainer,
    });
    const summary = render(Summary, { target: summaryContainer });

    return {
        user,
        chunkBody,
        summary,
        chunkBodyContainer,
        summaryContainer,
    };
}

test("Entities are loaded onto the summary", () => {
    setup();

    render(Summary);

    const t2 = get(resources).get("#T2");
    expect(t2).toBeDefined();
});

test("merging ATCC 25544", async () => {
    const { user, summary, chunkBody } = setup();

    expect(summary.queryByRole("button", { name: "ATCC" })).not.toBeNull();
    expect(summary.queryByRole("button", { name: "25544" })).not.toBeNull();
    expect(
        summary.queryByRole("button", { name: "ATCC 25544" }),
    ).not.toBeNull();

    await dragAndDrop(
        user,
        summary.getByRole("button", { name: "ATCC" }),
        summary.getByRole("button", { name: "ATCC 25544" }),
    );

    await dragAndDrop(
        user,
        summary.getByRole("button", { name: "25544" }),
        summary.getByRole("button", { name: "ATCC 25544" }),
    );

    expect(summary.queryByRole("button", { name: "ATCC" })).toBeNull();
    expect(summary.queryByRole("button", { name: "25544" })).toBeNull();
    expect(
        summary.queryByRole("button", { name: "ATCC 25544" }),
    ).not.toBeNull();

    const atccSpans = chunkBody
        .getAllByText("ATCC")
        .map((b) => b.parentElement);
    const numberSpans = chunkBody
        .getAllByText("25544")
        .map((b) => b.parentElement);

    atccSpans.forEach((span) =>
        expect(span.getAttribute("resource")).toEqual("#T10"),
    );
    numberSpans.forEach((span) =>
        expect(span.getAttribute("resource")).toEqual("#T10"),
    );
});
