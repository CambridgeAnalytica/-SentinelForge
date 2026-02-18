import { test, expect } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";

test.describe("Dashboard — Smoke Tests", () => {
    test.beforeEach(async ({ page }) => {
        await page.goto(BASE_URL);
    });

    test("loads the Scan Dashboard page", async ({ page }) => {
        await expect(page.locator("h2")).toContainText("Scan Dashboard");
    });

    test("displays stat cards", async ({ page }) => {
        const cards = page.locator('[class*="rounded-xl"]').filter({
            has: page.locator("text=Total Scans"),
        });
        await expect(cards.first()).toBeVisible();
    });

    test("shows Recent Scans table", async ({ page }) => {
        await expect(page.locator("th:has-text('Scenario')")).toBeVisible();
        await expect(page.locator("th:has-text('Target')")).toBeVisible();
        await expect(page.locator("th:has-text('Status')")).toBeVisible();
    });
});

test.describe("Dashboard — Navigation", () => {
    test("navigates to compliance page", async ({ page }) => {
        await page.goto(BASE_URL);
        // Click the compliance link in the sidebar
        await page.click("a[href='/compliance']");
        await expect(page.locator("h2")).toContainText("Compliance View");
    });

    test("navigates to schedules page", async ({ page }) => {
        await page.goto(BASE_URL);
        await page.click("a[href='/schedules']");
        await expect(page.locator("h2")).toContainText("Schedules");
    });

    test("navigates to drift page", async ({ page }) => {
        await page.goto(BASE_URL);
        await page.click("a[href='/drift']");
        await expect(page.locator("h2")).toContainText("Drift");
    });
});

test.describe("Dashboard — Attack Run Detail", () => {
    test("clicking a scan row navigates to detail page", async ({ page }) => {
        await page.goto(BASE_URL);
        // Wait for data to load, then click first scan row if any exist
        const firstRow = page.locator("tbody tr").first();
        const rowExists = await firstRow.isVisible().catch(() => false);
        if (rowExists) {
            const rowText = await firstRow.textContent();
            // Only click rows that have actual data, skip empty state
            if (rowText && !rowText.includes("No scans yet")) {
                await firstRow.click();
                await expect(page.url()).toContain("/attacks/");
                // Should show the back button
                await expect(page.locator("button")).toContainText("Back");
            }
        }
    });
});

test.describe("Compliance — Visualizations", () => {
    test("shows coverage stats and heatmap", async ({ page }) => {
        await page.goto(`${BASE_URL}/compliance`);
        await expect(page.locator("h2")).toContainText("Compliance View");
        // Should have coverage label
        await expect(page.locator("text=Coverage")).toBeVisible();
    });

    test("download PDF button is visible", async ({ page }) => {
        await page.goto(`${BASE_URL}/compliance`);
        const downloadBtn = page.locator("button:has-text('Download PDF')");
        await expect(downloadBtn).toBeVisible();
    });
});

test.describe("Schedules Page", () => {
    test("displays schedule list or empty state", async ({ page }) => {
        await page.goto(`${BASE_URL}/schedules`);
        await expect(page.locator("h2")).toContainText("Schedules");
    });
});
