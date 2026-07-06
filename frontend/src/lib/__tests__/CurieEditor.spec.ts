import { describe, test, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import CurieEditor from "$lib/components/CurieEditor.svelte";

async function open(container: HTMLElement): Promise<HTMLInputElement> {
    const trigger = container.querySelector(
        ".curie-display",
    ) as HTMLButtonElement;
    await fireEvent.click(trigger);
    return container.querySelector(".curie-input") as HTMLInputElement;
}

describe("CurieEditor", () => {
    test("shows the CURIE and no input until edit is triggered", () => {
        const { container } = render(CurieEditor, {
            props: { curie: "PROP:1", save: vi.fn() },
        });
        expect(container.querySelector("code")?.textContent).toBe("PROP:1");
        expect(container.querySelector(".curie-input")).toBeNull();
    });

    test("saves the trimmed new CURIE and closes on success", async () => {
        const save = vi.fn().mockResolvedValue(undefined);
        const { container } = render(CurieEditor, {
            props: { curie: "PROP:1", save },
        });

        const input = await open(container);
        await fireEvent.input(input, { target: { value: "  CHEBI:2  " } });
        await fireEvent.keyDown(input, { key: "Enter" });

        expect(save).toHaveBeenCalledWith("CHEBI:2");
        // Editor closed after success.
        expect(container.querySelector(".curie-input")).toBeNull();
    });

    test("shows the failure message inline and keeps the editor open", async () => {
        const save = vi
            .fn()
            .mockRejectedValue(new Error("CURIE 'CHEBI:2' is already in use"));
        const { container, findByText } = render(CurieEditor, {
            props: { curie: "PROP:1", save },
        });

        const input = await open(container);
        await fireEvent.input(input, { target: { value: "CHEBI:2" } });
        await fireEvent.keyDown(input, { key: "Enter" });

        await findByText("CURIE 'CHEBI:2' is already in use");
        // Editor stays open so the value can be corrected.
        expect(container.querySelector(".curie-input")).not.toBeNull();
    });

    test("Escape cancels without saving and clears any error", async () => {
        const save = vi.fn().mockRejectedValue(new Error("nope"));
        const { container, queryByText } = render(CurieEditor, {
            props: { curie: "PROP:1", save },
        });

        let input = await open(container);
        await fireEvent.input(input, { target: { value: "CHEBI:2" } });
        await fireEvent.keyDown(input, { key: "Enter" });
        await fireEvent.keyDown(input, { key: "Escape" });

        expect(container.querySelector(".curie-input")).toBeNull();
        expect(queryByText("nope")).toBeNull();

        // Re-opening starts clean (no stale error, value reset to the CURIE).
        input = await open(container);
        expect(input.value).toBe("PROP:1");
        expect(container.querySelector(".invalid-feedback")).toBeNull();
    });

    test("a double-Enter while saving fires only one save", async () => {
        let resolveSave: () => void = () => {};
        const save = vi.fn().mockReturnValue(
            new Promise<void>((resolve) => {
                resolveSave = resolve;
            }),
        );
        const { container } = render(CurieEditor, {
            props: { curie: "PROP:1", save },
        });

        const input = await open(container);
        await fireEvent.input(input, { target: { value: "CHEBI:2" } });
        // Two Enters before the in-flight save resolves.
        await fireEvent.keyDown(input, { key: "Enter" });
        await fireEvent.keyDown(input, { key: "Enter" });

        expect(save).toHaveBeenCalledTimes(1);
        resolveSave();
    });

    test("confirmUnchanged calls save with the current CURIE on an unchanged commit", async () => {
        const save = vi.fn().mockResolvedValue(undefined);
        const { container } = render(CurieEditor, {
            props: { curie: "PROP:1", save, confirmUnchanged: true },
        });

        const input = await open(container);
        await fireEvent.keyDown(input, { key: "Enter" }); // value unchanged

        expect(save).toHaveBeenCalledWith("PROP:1");
        expect(container.querySelector(".curie-input")).toBeNull();
    });

    test("confirmUnchanged still closes without saving on an empty value", async () => {
        const save = vi.fn();
        const { container } = render(CurieEditor, {
            props: { curie: "PROP:1", save, confirmUnchanged: true },
        });

        const input = await open(container);
        await fireEvent.input(input, { target: { value: "   " } });
        await fireEvent.keyDown(input, { key: "Enter" });

        expect(save).not.toHaveBeenCalled();
        expect(container.querySelector(".curie-input")).toBeNull();
    });

    test("an unchanged or empty value closes without calling save", async () => {
        const save = vi.fn();
        const { container } = render(CurieEditor, {
            props: { curie: "PROP:1", save },
        });

        const input = await open(container);
        await fireEvent.keyDown(input, { key: "Enter" }); // unchanged
        expect(save).not.toHaveBeenCalled();
        expect(container.querySelector(".curie-input")).toBeNull();

        const input2 = await open(container);
        await fireEvent.input(input2, { target: { value: "   " } });
        await fireEvent.keyDown(input2, { key: "Enter" }); // whitespace only
        expect(save).not.toHaveBeenCalled();
    });
});
