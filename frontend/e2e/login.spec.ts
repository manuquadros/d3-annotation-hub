import { test, expect } from "@playwright/test";

// These tests exercise the login form without a stored session.
test.use({ storageState: { cookies: [], origins: [] } });

test("valid credentials redirect away from login", async ({ page }) => {
    const username = process.env.E2E_USERNAME!;
    const password = process.env.E2E_PASSWORD!;

    await page.goto("/login");
    await page.fill("#username", username);
    await page.fill("#password", password);
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page).not.toHaveURL(/\/login/, { timeout: 10_000 });
});

test("wrong password shows error message", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#username", process.env.E2E_USERNAME!);
    await page.fill("#password", "definitely-not-the-right-password");
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page.locator(".error-message")).toBeVisible();
});

test("unauthenticated visit to / redirects to login", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
});
