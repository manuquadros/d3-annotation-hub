import { render, screen } from "@testing-library/svelte";
import { get } from "svelte/store";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";

import Summary from "./Summary.svelte";
import { classes, classLabels } from "./Summary.svelte";
import {
    resources,
    strainLabel,
    bacteriaLabel,
    enzymeLabel,
} from "$lib/resources.ts";
import { relations } from "$lib/relations.ts";
import { dragAndDrop } from "$lib/test_utils.ts";

test("no initial entities", () => {
    resources.reset();
    render(Summary);

    const button = screen.queryByRole("button");
    expect(button).not.toBeInTheDocument();
});

test("with entities", () => {
    resources.storeEntity(strainLabel, "#T1", "ATCC 25544");
    render(Summary);
    //render(html`<${Summary}` bind);

    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
});

function setup() {
    const user = userEvent.setup();

    resources.reset();
    resources.storeEntity(strainLabel, "#T1", "ATCC 25544");
    resources.storeEntity(strainLabel, "#T2", "ATCC25544");
    resources.storeEntity(enzymeLabel, "#T3", "cholesterol oxidase");
    resources.storeEntity(bacteriaLabel, "#T4", "Rhodococcus erythropolis");

    render(Summary);

    return user;
}

test("merging terms under the same resource", async () => {
    const user = setup();

    const strain1 = screen.getByRole("button", { name: "ATCC 25544" });
    const strain2 = screen.getByRole("button", { name: "ATCC25544" });

    await dragAndDrop(user, strain2, strain1);

    const t1 = get(resources).get("#T1");
    const t2 = get(resources).get("#T2");

    expect(t2).toBeUndefined();
    expect(t1.names).toContain("ATCC 25544");
    expect(t1.names).toContain("ATCC25544");
    expect(t1.name).toBe("ATCC 25544");
});

test("adding relations between classes", async () => {
    const user = setup();

    const strain = screen.getByRole("button", { name: "ATCC 25544" });
    const bacteria = screen.getByRole("button", {
        name: "Rhodococcus erythropolis",
    });
    const enzyme = screen.getByRole("button", { name: "cholesterol oxidase" });

    await dragAndDrop(user, strain, bacteria);
    await dragAndDrop(user, strain, enzyme);

    const hasEnzyme = get(relations).get("d3o:hasEnzyme");
    const hasSpecies = get(relations).get("d3o:hasSpecies");

    const t1 = get(resources).get("#T1");
    const t3 = get(resources).get("#T3");
    const t4 = get(resources).get("#T4");

    expect(hasEnzyme).toContainEqual({ subject: t1, object: t3 });
    expect(hasSpecies).toContainEqual({ subject: t1, object: t4 });
});
