import { test as setup, expect } from "@playwright/test";

setup("authenticate", async ({ page }) => {
    const username = process.env.E2E_USERNAME;
    const password = process.env.E2E_PASSWORD;
    if (!username || !password) {
        throw new Error(
            "E2E_USERNAME and E2E_PASSWORD must be set before running E2E tests.",
        );
    }

    const response = await page.request.post("/api/login", {
        multipart: { username, password },
    });
    expect(response.ok()).toBeTruthy();

    await page.context().storageState({ path: "e2e/.auth.json" });
});
