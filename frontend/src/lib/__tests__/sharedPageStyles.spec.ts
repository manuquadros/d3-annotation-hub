import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import SettingsPage from "../../routes/settings/+page.svelte";
import NewProjectPage from "../../routes/projects/new/+page.svelte";

vi.mock("$app/navigation", () => ({
    goto: vi.fn(() => Promise.resolve()),
    invalidateAll: vi.fn(() => Promise.resolve()),
}));

vi.mock("$lib/api", () => ({
    setLastProject: vi.fn(() => Promise.resolve()),
}));

function json(body: unknown, status = 200): Response {
    return new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
    fetchMock = vi.fn(() => Promise.resolve(json({})));
    vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
});

/*
 * The scoped <style> blocks are not evaluated under vitest (no `css: true`),
 * so the width contract is pinned against the component source instead of
 * getComputedStyle, which would pass vacuously.
 */
function pageSource(route: string): string {
    // vitest runs with `frontend/` as cwd; import.meta.url is vite-rooted
    // ("/src/...") and is not a usable filesystem path here.
    return readFileSync(
        resolve(process.cwd(), `src/routes/${route}/+page.svelte`),
        "utf-8",
    );
}

function scopedStyleBlock(source: string): string {
    const block = /<style>([\s\S]*)<\/style>/.exec(source);
    expect(block).not.toBeNull();
    return block![1];
}

/*
 * These pages used to carry private copies of `.card`/`.field`/`.optional`/
 * `.error`/`.success` in their own <style> blocks. The contract asserted here
 * is structural, not visual: the markup must use the shared design-system class
 * names so that management.css / Digidive actually reach it.
 */
describe("settings page uses the shared design system", () => {
    test("root is .page and the form sits in a shared .card", () => {
        const { container } = render(SettingsPage);

        const root = container.firstElementChild as HTMLElement;
        expect(root.classList.contains("page")).toBe(true);
        expect(container.querySelector(".settings-page")).toBeNull();

        const card = container.querySelector(".card");
        expect(card).not.toBeNull();
        expect(card?.querySelector("form")).not.toBeNull();
    });

    test("every password input is a .field with a Digidive .form-control", () => {
        const { container } = render(SettingsPage);

        const fields = container.querySelectorAll(".field");
        expect(fields).toHaveLength(3);

        for (const field of fields) {
            expect(field.querySelector("label")).not.toBeNull();
            const input = field.querySelector("input");
            expect(input).not.toBeNull();
            expect(input?.classList.contains("form-control")).toBe(true);
        }
    });

    test("mismatched passwords render the shared .error region", async () => {
        const { container } = render(SettingsPage);

        await fireEvent.input(container.querySelector("#cp-new")!, {
            target: { value: "correct-horse" },
        });
        await fireEvent.input(container.querySelector("#cp-confirm")!, {
            target: { value: "battery-staple" },
        });
        await fireEvent.submit(container.querySelector("form")!);

        await waitFor(() => {
            const error = container.querySelector("p.error");
            expect(error?.textContent).toContain("do not match");
        });
        expect(fetchMock).not.toHaveBeenCalled();
    });

    test("a successful change renders the shared .success region", async () => {
        const { container } = render(SettingsPage);

        await fireEvent.submit(container.querySelector("form")!);

        await waitFor(() => {
            expect(container.querySelector("p.success")).not.toBeNull();
        });
    });

    test("keeps the narrow form width layered on top of shared .page", () => {
        const source = pageSource("settings");
        expect(source).toContain('import "$lib/styles/management.css"');

        const styles = scopedStyleBlock(source);
        expect(styles).toMatch(/\.page\s*\{[^}]*max-width:\s*480px/);
        // Only the width is overridden; margin/padding/flex stay shared.
        expect(styles).not.toMatch(/\.page\s*\{[^}]*(margin|padding|display):/);
    });
});

describe("new-project page uses the shared design system", () => {
    test("root is .page and the form sits in a shared .card", () => {
        const { container } = render(NewProjectPage);

        const root = container.firstElementChild as HTMLElement;
        expect(root.classList.contains("page")).toBe(true);
        expect(container.querySelector(".new-project-page")).toBeNull();

        const card = container.querySelector(".card");
        expect(card).not.toBeNull();
        expect(card?.querySelector("form")).not.toBeNull();
    });

    test("fields use .field/.optional and Digidive .form-control", () => {
        const { container } = render(NewProjectPage);

        const fields = container.querySelectorAll(".field");
        expect(fields).toHaveLength(3);

        for (const field of fields) {
            expect(field.querySelector("label")).not.toBeNull();
            const input = field.querySelector("input");
            expect(input?.classList.contains("form-control")).toBe(true);
        }

        const optional = container.querySelector(".field label .optional");
        expect(optional?.textContent).toContain("optional");

        // Page-specific narrowing stays local, layered on the shared .field.
        const narrow = container.querySelector(".field-narrow");
        expect(narrow?.classList.contains("field")).toBe(true);
    });

    test("a failed create renders the shared .error region", async () => {
        fetchMock.mockResolvedValue(
            json({ detail: "Name already taken" }, 400),
        );
        const { container } = render(NewProjectPage);

        await fireEvent.submit(container.querySelector("form")!);

        await waitFor(() => {
            const error = container.querySelector("p.error");
            expect(error?.textContent).toContain("Name already taken");
        });
    });

    test("keeps the narrow form width layered on top of shared .page", () => {
        const source = pageSource("projects/new");
        expect(source).toContain('import "$lib/styles/management.css"');

        const styles = scopedStyleBlock(source);
        expect(styles).toMatch(/\.page\s*\{[^}]*max-width:\s*480px/);
        // Only the width is overridden; margin/padding/flex stay shared.
        expect(styles).not.toMatch(/\.page\s*\{[^}]*(margin|padding|display):/);
    });
});
