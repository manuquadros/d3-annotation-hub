import { describe, it, expect } from "vitest";
import { canManageProject } from "$lib/utils/projectAccess";

const base = {
    isAdmin: false,
    isProjectManager: false,
    currentProjectId: null as number | null,
};

describe("canManageProject", () => {
    it("allows a global admin regardless of project", () => {
        expect(canManageProject({ ...base, isAdmin: true }, 5)).toBe(true);
    });

    it("allows a manager of this project", () => {
        expect(
            canManageProject(
                { ...base, isProjectManager: true, currentProjectId: 5 },
                5,
            ),
        ).toBe(true);
    });

    it("denies a manager of a different project (query-param override)", () => {
        // isProjectManager was resolved against project 9 via ?project=9, but
        // the page is for project 5 — must not grant access.
        expect(
            canManageProject(
                { ...base, isProjectManager: true, currentProjectId: 9 },
                5,
            ),
        ).toBe(false);
    });

    it("denies a plain member / annotator", () => {
        expect(canManageProject({ ...base, currentProjectId: 5 }, 5)).toBe(
            false,
        );
    });
});
