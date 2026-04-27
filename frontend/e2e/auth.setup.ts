import { test as setup, expect } from "@playwright/test";

setup("authenticate", async ({ page }) => {
    const username = process.env.E2E_USERNAME;
    const password = process.env.E2E_PASSWORD;
    if (!username || !password) {
        throw new Error(
            "E2E_USERNAME and E2E_PASSWORD must be set before running E2E tests.",
        );
    }

    await page.goto("/login");
    await page.fill("#username", username);
    await page.fill("#password", password);
    await page.getByRole("button", { name: "Sign In" }).click();

    // Login calls window.location.replace("/"), then / may redirect further.
    await expect(page).not.toHaveURL(/\/login/, { timeout: 10_000 });

    await page.context().storageState({ path: "e2e/.auth.json" });
});
