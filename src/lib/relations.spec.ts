import { describe, expect, test } from "vitest";
import { relations } from "$lib/relations.ts";

describe("relations", () => {
    const t1 = { label: "strain", count: 1, names: new Set(["aaa"]) };
    const t2 = { label: "bacteria", count: 1, names: new Set(["bbb"]) };
    const t3 = { label: "bacteria", count: 1, names: new Set(["ccc"]) };

    let size: number;
    let otherSize: number;

    relations.subscribe((relations) => (size = relations.size));

    relations.add(t1, "strainOf", t2);

    test("relations store works", () => {
        expect(size).toBe(1);
        relations.add(t2, "sameAs", t3);
        expect(size).toBe(2);
    });
});
