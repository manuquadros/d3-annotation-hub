import { describe, test, expect } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import ClassPicker from "$lib/components/ClassPicker.svelte";
import type { KindOption } from "$lib/api.ts";

const OPTIONS: KindOption[] = [
    { curie: "d3o:Strain", label: "Strain" },
    { curie: "d3o:Bacteria", label: "Bacteria" },
    { curie: "d3o:Enzyme", label: "Enzyme" },
];

function input(container: HTMLElement): HTMLInputElement {
    return container.querySelector("input") as HTMLInputElement;
}

describe("ClassPicker", () => {
    test("renders a pre-selected value as its formatted label", () => {
        const { container } = render(ClassPicker, {
            props: { value: "d3o:Strain", options: OPTIONS },
        });
        expect(input(container).value).toBe("Strain (d3o:Strain)");
    });

    test("editing a pre-selected value keeps the typed text (no wipe, no eaten keystroke)", async () => {
        // Regression for TICKET-28: the sync effect used to re-run when
        // handleInput cleared `value`, blanking the input and dropping the
        // just-typed character.
        const { container } = render(ClassPicker, {
            props: { value: "d3o:Strain", options: OPTIONS },
        });
        const el = input(container);
        expect(el.value).toBe("Strain (d3o:Strain)");

        await fireEvent.input(el, {
            target: { value: "Strain (d3o:Strain)x" },
        });

        expect(el.value).toBe("Strain (d3o:Strain)x");
    });

    test("late-loading options upgrade a bare CURIE to its label", async () => {
        const { container, rerender } = render(ClassPicker, {
            props: { value: "d3o:Strain", options: [] },
        });
        // Before options arrive the input can only show the raw CURIE.
        expect(input(container).value).toBe("d3o:Strain");

        await rerender({ value: "d3o:Strain", options: OPTIONS });

        expect(input(container).value).toBe("Strain (d3o:Strain)");
    });

    test("does not clobber in-progress typing when options load late", async () => {
        const { container, rerender } = render(ClassPicker, {
            props: { value: "", options: [] },
        });
        const el = input(container);
        await fireEvent.input(el, { target: { value: "bact" } });
        expect(el.value).toBe("bact");

        // Options resolving must not overwrite what the user is typing.
        await rerender({ value: "", options: OPTIONS });

        expect(el.value).toBe("bact");
    });

    test("picking an option shows its formatted label", async () => {
        const { container } = render(ClassPicker, {
            props: { value: "", options: OPTIONS },
        });
        const el = input(container);
        await fireEvent.focus(el);
        await fireEvent.input(el, { target: { value: "bact" } });

        const option = container.querySelector(
            ".dropdown li button",
        ) as HTMLButtonElement;
        await fireEvent.mouseDown(option);

        expect(el.value).toBe("Bacteria (d3o:Bacteria)");
    });
});
