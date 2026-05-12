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
    await expect(page.locator(".reference-meta h1")).toBeVisible();
});

test("class picker ranks prefix matches before contains matches", async ({
    page,
}) => {
    await page.goto("/");
    await page.waitForURL((url) => url.searchParams.has("ref"), {
        timeout: 10_000,
    });

    await page.locator(".queue-row a").first().click();
    await expect(page.locator(".reference-meta h1")).toBeVisible();

    const articleBody = page.locator("#article-body").first();
    await expect(articleBody).toBeVisible();
    const box = await articleBody.boundingBox();
    await page.mouse.move(box!.x + 10, box!.y + 10);
    await page.mouse.down();
    await page.mouse.move(box!.x + 60, box!.y + 10);
    await page.mouse.up();

    await page.locator(".tabs button", { hasText: "New entity" }).click();

    const classInput = page.locator(".class-picker input");
    await classInput.fill("bact");

    const firstOption = page.locator(".class-picker .dropdown li").first();
    await expect(firstOption).toBeVisible();

    const firstLabel = await firstOption.locator(".opt-label").textContent();
    expect(firstLabel?.toLowerCase()).toMatch(/^bact/);
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
