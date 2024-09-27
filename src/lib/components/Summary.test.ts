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

test("no initial entities", () => {
    resources.reset();
    render(Summary);

    const button = screen.queryByRole("button");
    expect(button).not.toBeInTheDocument();
});

test("with entities", () => {
    resources.storeEntity(strainLabel, "#T1", "ATC 25544");
    render(Summary);
    //render(html`<${Summary}` bind);

    const button = screen.getByRole("button");
    expect(button).toBeInTheDocument();
});

function setup() {
    const user = userEvent.setup();

    resources.reset();
    resources.storeEntity(strainLabel, "#T1", "ATC 25544");
    resources.storeEntity(strainLabel, "#T2", "ATC25544");
    resources.storeEntity(enzymeLabel, "#T3", "cholesterol oxidase");
    resources.storeEntity(bacteriaLabel, "#T4", "Rhodococcus erythropolis");

    render(Summary);

    return user;
}

test("merging terms under the same resource", async () => {
    const user = setup();

    const strain1 = screen.getByRole("button", { name: "ATC 25544" });
    const strain2 = screen.getByRole("button", { name: "ATC25544" });

    await user.pointer([
        { target: strain1, keys: "[MouseLeft>]" },
        { target: strain2 },
        { target: strain2, keys: "[/MouseLeft]" },
    ]);

    const t1 = get(resources).get("#T1");
    const t2 = get(resources).get("#T2");

    expect(t1).toBeUndefined;
    expect(t2.names).toContain("ATC 25544");
    expect(t2.names).toContain("ATC25544");
    expect(t2.name).toBe("ATC 25544");
});

test("adding relations between classes", async () => {
    const user = setup();

    const strain = screen.getByRole("button", { name: "ATC 25544" });
    const bacteria = screen.getByRole("button", {
        name: "Rhodococcus erythropolis",
    });
    const enzyme = screen.getByRole("button", { name: "cholesterol oxidase" });

    await user.pointer([
        { target: strain, keys: "[MouseLeft>]" },
        { target: bacteria },
        { target: bacteria, keys: "[/MouseLeft]" },
        { target: strain, keys: "[MouseLeft>]" },
        { target: enzyme },
        { target: enzyme, keys: "[/MouseLeft]" },
    ]);

    const t1 = get(resources).get("#T1");
    const t3 = get(resources).get("#T3");
    const t4 = get(resources).get("#T4");

    const hasEnzyme = get(relations).get("d3o:hasEnzyme");
    const hasSpecies = get(relations).get("d3o:hasSpecies");

    expect(hasEnzyme).toContain({ subject: t1, object: t3 });
    expect(hasSpecies).toContain({ subject: t1, object: t4 });
});
