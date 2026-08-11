import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/svelte";
import { invalidateAll } from "$app/navigation";
import AdminPage from "../../routes/admin/+page.svelte";
import ProjectUsersPage from "../../routes/projects/[id]/users/+page.svelte";

vi.mock("$app/navigation", () => ({
    invalidateAll: vi.fn(() => Promise.resolve()),
    goto: vi.fn(() => Promise.resolve()),
}));

const invalidateAllMock = vi.mocked(invalidateAll);

type Handler = (url: string, init?: RequestInit) => Response;

let handler: Handler;

function ok(body: unknown): Response {
    return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
}

function fail(status = 500, detail = "nope"): Response {
    return new Response(JSON.stringify({ detail }), {
        status,
        headers: { "Content-Type": "application/json" },
    });
}

function member(over: Partial<Record<string, unknown>> = {}) {
    return {
        user_id: "u1",
        email: "manager@example.com",
        roles: ["annotator"],
        ...over,
    };
}

// Both pages receive the layout's role flags merged into `data`.
const layoutData = {
    authenticated: true,
    isSuperuser: true as const,
    isAdmin: true,
    isCurator: false,
    isAnnotator: true,
    isProjectManager: true,
    currentProjectId: 7,
    email: "manager@example.com",
};

function usersPageData(members = [member()]) {
    return { ...layoutData, projects: [], projectId: 7, members };
}

function adminPageData() {
    return {
        ...layoutData,
        isProjectCreator: true,
        projects: [
            {
                project_id: 7,
                name: "Enzymes",
                description: null,
                required_annotators: 2,
            },
        ],
        allUsers: [],
        ontologies: [],
        proposedEntities: [],
        proposedTotal: 0,
    };
}

function button(container: HTMLElement, label: string): HTMLButtonElement {
    const match = [...container.querySelectorAll("button")].find(
        (b) => b.textContent?.replace(/\s+/g, " ").trim() === label,
    );
    if (!match) throw new Error(`no button labelled "${label}"`);
    return match as HTMLButtonElement;
}

beforeEach(() => {
    invalidateAllMock.mockClear();
    handler = () => ok({});
    vi.stubGlobal(
        "fetch",
        vi.fn((input: RequestInfo | URL, init?: RequestInit) =>
            Promise.resolve(handler(String(input), init)),
        ),
    );
});

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("project membership mutations refresh the layout", () => {
    test("removing a user from a project calls invalidateAll", async () => {
        const { container } = render(ProjectUsersPage, {
            props: { data: usersPageData() },
        });

        await fireEvent.click(button(container, "Remove user"));
        await fireEvent.click(button(container, "Yes"));

        await waitFor(() => expect(invalidateAllMock).toHaveBeenCalledTimes(1));
    });

    test("a failed removal does not call invalidateAll", async () => {
        handler = (_url, init) =>
            init?.method === "DELETE" ? fail(403) : ok({});
        const { container } = render(ProjectUsersPage, {
            props: { data: usersPageData() },
        });

        await fireEvent.click(button(container, "Remove user"));
        await fireEvent.click(button(container, "Yes"));

        await waitFor(() =>
            expect(container.textContent).toContain("Failed to remove user"),
        );
        expect(invalidateAllMock).not.toHaveBeenCalled();
    });

    test("adding a member calls invalidateAll", async () => {
        handler = (url, init) => {
            if (init?.method === "POST")
                return ok(member({ user_id: "u2", email: "new@example.com" }));
            if (url.includes("/users/search"))
                return ok([{ user_id: "u2", email: "new@example.com" }]);
            return ok([]);
        };
        const { container } = render(ProjectUsersPage, {
            props: { data: usersPageData() },
        });

        const search = container.querySelector(
            'input[type="search"]',
        ) as HTMLInputElement;
        await fireEvent.input(search, { target: { value: "new@example.com" } });

        const option = await waitFor(
            () => {
                const li = container.querySelector('li[role="option"]');
                if (!li) throw new Error("suggestion not rendered");
                return li;
            },
            { timeout: 2000 },
        );
        await fireEvent.mouseDown(option);

        const form = container.querySelector(
            "form.add-form",
        ) as HTMLFormElement;
        await fireEvent.submit(form);

        await waitFor(() => expect(invalidateAllMock).toHaveBeenCalledTimes(1));
    });

    test("the member table re-syncs when reloaded page data arrives", async () => {
        const { container, rerender } = render(ProjectUsersPage, {
            props: { data: usersPageData() },
        });
        expect(container.textContent).toContain("manager@example.com");

        await rerender({
            data: usersPageData([
                member({ user_id: "u9", email: "reloaded@example.com" }),
            ]),
        });

        await waitFor(() =>
            expect(container.textContent).toContain("reloaded@example.com"),
        );
        expect(container.textContent).not.toContain("manager@example.com");
    });
});

describe("admin project mutations refresh the layout", () => {
    test("deleting a project calls invalidateAll", async () => {
        const { container } = render(AdminPage, {
            props: { data: adminPageData() },
        });

        await fireEvent.click(button(container, "Remove"));
        await fireEvent.click(button(container, "Yes"));

        await waitFor(() => expect(invalidateAllMock).toHaveBeenCalledTimes(1));
    });

    test("a failed project deletion does not call invalidateAll", async () => {
        handler = (_url, init) =>
            init?.method === "DELETE" ? fail(409) : ok({});
        const { container } = render(AdminPage, {
            props: { data: adminPageData() },
        });

        await fireEvent.click(button(container, "Remove"));
        await fireEvent.click(button(container, "Yes"));

        await waitFor(() => expect(button(container, "Remove")).toBeTruthy());
        expect(invalidateAllMock).not.toHaveBeenCalled();
    });

    test("granting a project role calls invalidateAll", async () => {
        handler = (_url, init) =>
            init?.method === "POST"
                ? ok(member({ user_id: "u2", email: "new@example.com" }))
                : ok([]);
        const { container } = render(AdminPage, {
            props: { data: adminPageData() },
        });

        await fireEvent.click(button(container, "Manage"));
        const form = await waitFor(() => {
            const f = container.querySelector("form.inline-form");
            if (!f) throw new Error("member form not rendered");
            return f as HTMLFormElement;
        });
        const email = form.querySelector(
            'input[type="email"]',
        ) as HTMLInputElement;
        await fireEvent.input(email, { target: { value: "new@example.com" } });
        await fireEvent.submit(form);

        await waitFor(() => expect(invalidateAllMock).toHaveBeenCalledTimes(1));
    });

    test("revoking a project role calls invalidateAll", async () => {
        handler = (_url, init) =>
            init?.method === "DELETE" ? ok({}) : ok([member()]);
        const { container } = render(AdminPage, {
            props: { data: adminPageData() },
        });

        await fireEvent.click(button(container, "Manage"));
        const remove = await waitFor(() =>
            button(container, "Remove annotator"),
        );
        await fireEvent.click(remove);

        await waitFor(() => expect(invalidateAllMock).toHaveBeenCalledTimes(1));
    });
});
