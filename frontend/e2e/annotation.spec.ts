import { test, expect } from "@playwright/test";

test("annotation queue shows references in the sidebar", async ({ page }) => {
    await page.goto("/");
    // Root redirects to /?ref=...&project=... for annotators.
    await page.waitForURL((url) => url.searchParams.has("ref"), {
        timeout: 10_000,
    });
    await expect(page.locator(".queue-row a").first()).toBeVisible();
});

test("clicking a queue item loads the article", async ({ page }) => {
    await page.goto("/");
    await page.waitForURL((url) => url.searchParams.has("ref"), {
        timeout: 10_000,
    });

    const firstLink = page.locator(".queue-row a").first();
    const expectedHref = await firstLink.getAttribute("href");
    await firstLink.click();

    await expect(page).toHaveURL(expectedHref!);
    await expect(page.locator(".reference-meta h2")).toBeVisible();
});

test("check button marks a queue item complete and back to incomplete", async ({
    page,
}) => {
    await page.goto("/");
    await page.waitForURL((url) => url.searchParams.has("ref"), {
        timeout: 10_000,
    });

    // Capture the ref text so we can track the item after it moves between the
    // incomplete and completed sections of the queue (different DOM elements).
    const firstLink = page.locator(".queue-row a:not(.done)").first();
    await expect(firstLink).toBeVisible();
    const refText = (await firstLink.textContent())!.trim();

    const row = page.locator(".queue-row", { hasText: refText });

    // The check button is opacity-0 by default; hovering reveals it.
    await row.hover();
    await row.locator(".check-btn").click();
    // Completion is reflected by the .done class on the link, not the button class.
    await expect(row.locator("a")).toHaveClass(/done/);

    // Undo to leave the dev database in its original state.
    await row.hover();
    await row.locator(".check-btn").click();
    await expect(row.locator("a")).not.toHaveClass(/done/);
});
