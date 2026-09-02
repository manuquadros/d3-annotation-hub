import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import SettingsPage from "../../routes/settings/+page.svelte";
import NewProjectPage from "../../routes/projects/new/+page.svelte";
import AdminPage from "../../routes/admin/+page.svelte";
import HubPage from "../../routes/+page.svelte";
import ProjectHubPage from "../../routes/projects/[id]/+page.svelte";

vi.mock("$app/stores", async () => {
    const { readable } = await import("svelte/store");
    return {
        page: readable({
            params: { id: "p1" },
            url: new URL("http://localhost/projects/p1"),
        }),
    };
});

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
const srcDir = resolve(dirname(fileURLToPath(import.meta.url)), "../..");

function readSource(relPath: string): string {
    return readFileSync(resolve(srcDir, relPath), "utf-8");
}

function pageSource(route: string): string {
    return readSource(`routes/${route}/+page.svelte`);
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

describe("the stacked-form layout is shared, not copied", () => {
    const stackedFormUsers = [
        ["settings page", "routes/settings/+page.svelte"],
        ["new-project page", "routes/projects/new/+page.svelte"],
        ["ontology import form", "lib/components/OntologyImportForm.svelte"],
    ] as const;

    test("management.css defines the .stacked-form rule", () => {
        const css = readSource("lib/styles/management.css");

        const rule = /\.stacked-form\s*\{([^}]*)\}/.exec(css);
        expect(rule).not.toBeNull();
        expect(rule![1]).toMatch(/display:\s*flex/);
        expect(rule![1]).toMatch(/flex-direction:\s*column/);
        expect(rule![1]).toMatch(/gap:\s*0\.75rem/);
    });

    test.each(stackedFormUsers)(
        "%s declares no private copy of the form layout",
        (_name, relPath) => {
            const styles = scopedStyleBlock(readSource(relPath));

            expect(styles).not.toMatch(/(^|[\s,>])form\s*\{/);
        },
    );

    test.each(stackedFormUsers)(
        "%s opts into .stacked-form and imports management.css",
        (_name, relPath) => {
            const source = readSource(relPath);

            expect(source).toContain('import "$lib/styles/management.css"');
            expect(source).toMatch(/<form[^>]*class="[^"]*\bstacked-form\b/);
        },
    );
});

describe("the stacked-form layout reaches the rendered markup", () => {
    test("the settings form carries .stacked-form", () => {
        const { container } = render(SettingsPage);

        expect(container.querySelector("form.stacked-form")).not.toBeNull();
    });

    test("the new-project form carries .stacked-form", () => {
        const { container } = render(NewProjectPage);

        expect(container.querySelector("form.stacked-form")).not.toBeNull();
    });
});

describe("admin page uses the shared design system", () => {
    const adminData = {
        authenticated: true,
        isAdmin: true,
        isAnnotator: false,
        isCurator: false,
        isProjectManager: false,
        currentProjectId: null,
        isSuperuser: true as const,
        isProjectCreator: true,
        projects: [],
        allUsers: [],
        ontologies: [],
        proposedEntities: [],
        proposedTotal: 0,
    };

    /*
     * Every one of these was a private copy in the admin <style> block, several
     * with values that had drifted from the shared sheet.
     */
    const sharedSelectors = [
        ".card",
        ".field",
        ".error",
        ".success",
        ".empty",
        ".hint",
        "table",
        "th",
        "td",
        "label",
        "h1",
        "h2",
    ];

    test("imports management.css and roots on .page", () => {
        const source = pageSource("admin");

        expect(source).toContain('import "$lib/styles/management.css"');
        expect(source).toContain('<div class="page">');
        expect(source).not.toContain("admin-page");
    });

    test.each(sharedSelectors)(
        "declares no private copy of `%s`",
        (selector) => {
            const styles = scopedStyleBlock(pageSource("admin"));
            const rule = new RegExp(
                `^\\s*${selector.replace(".", "\\.")}\\s*[,{]`,
                "m",
            );

            expect(styles).not.toMatch(rule);
        },
    );

    test("management.css supplies the table rules admin now relies on", () => {
        const css = readSource("lib/styles/management.css");

        expect(css).toMatch(/\.page table\s*\{[^}]*width:\s*100%/);
        expect(css).toMatch(/\.page th\s*\{/);
        expect(css).toMatch(/\.page td\s*\{/);
    });

    test("keeps the nested-table overrides that layer on .page th/td", () => {
        const styles = scopedStyleBlock(pageSource("admin"));

        expect(styles).toMatch(/\.inner-table th\s*\{/);
        expect(styles).toMatch(/\.entity-table th\s*\{/);
        // The 2px header rule they used to undo is gone with the local copy.
        expect(styles).not.toContain("border-bottom-width");
    });

    test("root is .page and every section is a shared .card", () => {
        const { container } = render(AdminPage, { props: { data: adminData } });

        const root = container.firstElementChild as HTMLElement;
        expect(root.classList.contains("page")).toBe(true);
        expect(container.querySelector(".admin-page")).toBeNull();
        expect(
            container.querySelectorAll(".page > section.card").length,
        ).toBeGreaterThan(1);
    });

    test("empty sections use the shared .empty region", () => {
        const { container } = render(AdminPage, { props: { data: adminData } });

        const empties = container.querySelectorAll("p.empty");
        expect(empties.length).toBeGreaterThan(0);
    });

    test("the add-user fields are shared .field wrappers", async () => {
        fetchMock.mockResolvedValue(json("correct-horse-battery-staple"));
        const { container } = render(AdminPage, { props: { data: adminData } });

        const toggle = [...container.querySelectorAll("button")].find((b) =>
            b.textContent?.includes("Add user"),
        );
        await fireEvent.click(toggle!);

        const form = container.querySelector("form.add-user-form");
        expect(form).not.toBeNull();
        const fields = form!.querySelectorAll(".field");
        expect(fields).toHaveLength(2);
        for (const field of fields) {
            expect(field.querySelector("label")).not.toBeNull();
        }
    });

    test("tables sit inside .page so the shared table rules reach them", () => {
        const { container } = render(AdminPage, {
            props: {
                data: {
                    ...adminData,
                    allUsers: [
                        {
                            user_id: "u1",
                            email: "a@example.com",
                            is_super_user: false,
                            can_manage: false,
                            disabled: false,
                        },
                    ],
                },
            },
        });

        const table = container.querySelector("table");
        expect(table).not.toBeNull();
        expect(table?.closest(".page")).not.toBeNull();
        expect(table?.querySelector("th")).not.toBeNull();
    });
});

/*
 * Both hub pages used to carry a byte-identical 87-line <style> block plus a
 * copy of the card markup. The shared sheet is not an option here: the root
 * route also renders the annotation UI, whose AnnotationEditor uses `.field`,
 * `.empty` and `.hint` for unrelated things, so importing management.css there
 * would restyle it. The card therefore lives in a component of its own.
 */
describe("the hub pages share one nav-card component", () => {
    const hubPages = [
        ["root hub", "routes/+page.svelte"],
        ["project hub", "routes/projects/[id]/+page.svelte"],
    ] as const;

    const navCardSelectors = [
        ".hub",
        ".cards",
        ".card",
        ".card-icon",
        ".card-body",
        ".card-arrow",
    ];

    function sourceFiles(): string[] {
        return readdirSync(srcDir, { recursive: true, encoding: "utf-8" })
            .filter((rel) => rel.endsWith(".svelte") || rel.endsWith(".css"))
            .map((rel) => rel.replaceAll("\\", "/"));
    }

    test("NavCards declares the whole hub layout", () => {
        const styles = scopedStyleBlock(
            readSource("lib/components/NavCards.svelte"),
        );

        for (const selector of navCardSelectors) {
            expect(styles).toMatch(
                new RegExp(`^\\s*\\${selector}\\s*[,:{ ]`, "m"),
            );
        }
    });

    /*
     * `.card` is left out: management.css owns that name for the static
     * management panel, which is a different object that happens to share the
     * word. The rest are the hub's alone.
     */
    const soleOwnerSelectors = navCardSelectors.filter(
        (selector) => selector !== ".card",
    );

    test.each(soleOwnerSelectors)(
        "`%s` is declared in exactly one file",
        (selector) => {
            const rule = new RegExp(`^\\s*\\${selector}\\s*[,:{ ]`, "m");
            const owners = sourceFiles().filter((rel) =>
                rule.test(readSource(rel)),
            );

            expect(owners).toEqual(["lib/components/NavCards.svelte"]);
        },
    );

    test.each(hubPages)(
        "%s delegates its cards to NavCards and keeps no styles of its own",
        (_name, relPath) => {
            const source = readSource(relPath);

            expect(source).toContain(
                'import NavCards from "$lib/components/NavCards.svelte"',
            );
            expect(source).toContain("<NavCards");
            expect(source).not.toContain("<style>");
        },
    );

    test("the root hub renders one card per destination", () => {
        const { container } = render(HubPage, {
            props: {
                data: {
                    ...layoutData,
                    mode: "hub" as const,
                    destinations: ["annotate", "curate", "manage", "admin"],
                    documentData: null,
                },
            },
        });

        expect(container.querySelector(".hub h1")?.textContent).toBe(
            "Where would you like to go?",
        );

        const cards = container.querySelectorAll(".cards > a.card");
        expect(cards).toHaveLength(4);
        expect([...cards].map((card) => card.getAttribute("href"))).toEqual([
            "/?go=annotate&project=1",
            "/curate?project=1",
            "/projects/1",
            "/admin",
        ]);

        for (const card of cards) {
            expect(card.querySelector(".card-icon i.ph")).not.toBeNull();
            expect(
                card.querySelector(".card-body h2")?.textContent,
            ).toBeTruthy();
            expect(
                card.querySelector(".card-body p")?.textContent,
            ).toBeTruthy();
            expect(card.querySelector("i.card-arrow")).not.toBeNull();
        }
    });

    const layoutData = {
        authenticated: true,
        isSuperuser: false,
        isAdmin: false,
        isCurator: false,
        isAnnotator: true,
        isProjectManager: true,
        projects: [],
        currentProjectId: 1,
    };

    const projectHubData = { ...layoutData, projectName: "My Project" };

    test("the project hub renders the three management cards", () => {
        const { container } = render(ProjectHubPage, {
            props: { data: projectHubData },
        });

        expect(container.querySelector(".hub h1")?.textContent).toBe(
            "My Project",
        );

        const cards = [...container.querySelectorAll(".cards > a.card")];
        expect(cards.map((card) => card.getAttribute("href"))).toEqual([
            "/projects/p1/documents",
            "/projects/p1/ontologies",
            "/projects/p1/users",
        ]);
        expect(
            cards.map(
                (card) => card.querySelector(".card-body h2")?.textContent,
            ),
        ).toEqual(["Documents", "Ontologies", "Users"]);

        for (const card of cards) {
            expect(card.querySelector(".card-icon i.ph")).not.toBeNull();
            expect(card.querySelector("i.card-arrow")).not.toBeNull();
        }
    });

    test("the project hub falls back to a generic heading", () => {
        const { container } = render(ProjectHubPage, {
            props: { data: { ...projectHubData, projectName: null } },
        });

        expect(container.querySelector(".hub h1")?.textContent).toBe(
            "Project Management",
        );
    });
});
