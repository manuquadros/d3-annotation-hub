import { expect, test } from "vitest";
import { JSDOM } from "jsdom";
import { get } from "svelte/store";
import {
    resources,
    resourceCounter,
    strainLabel,
    bacteriaLabel,
    enzymeLabel,
} from "$lib/resources.ts";

const mockdoc = new JSDOM(`
<!DOCTYPE html><html><body>
<span class="entity" typeof="${bacteriaLabel}" resource="#T3">Escherichia coli</span>
</body></html>`);
global.document = mockdoc.window.document;

const span = document.querySelector("span");

let resourceCount: number;
resources.subscribe((resources) => (resourceCount = resources.size));

resources.storeEntity(strainLabel, "#T1", "ATC25544");
resources.storeEntity(strainLabel, "#T1", "ATC 25544");
resources.storeEntity(enzymeLabel, "#T2", "cholesterol oxidase");
resources.storeEntitySpan(span);

describe("resource store", () => {
    test("resources can be added to the store", () => {
        expect(resourceCount).toBe(3);
    });

    test("resource is correctly named", () => {
        expect(get(resources).get("#T1").name).toBe("ATC 25544");
    });

    test("remove entity", () => {
        resources.removeEntity("#T2");
        expect(resourceCount).toBe(2);
    });

    test("remove entity span", () => {
        resources.removeEntitySpan(span);
        expect(resourceCount).toBe(1);
    });

    test("find resource", () => {
        expect(resources.find("ATC 25544")).toBe("#T1");
        expect(resources.find("ATC 4277")).toBeNull;
    });

    test("merge resources", () => {
        resources.storeEntity(strainLabel, "#T4", "ATC 4277");
        expect(resources.find("ATC 4277")).toBe("#T4");
        resources.merge("#T4", "#T1");
        expect(get(resources).has("#T4")).toBe(false);
        expect(get(resources).get("#T1").names).toContain("ATC 4277");
        expect(resources.find("ATC 4277")).toBe("#T1");
    });
});
