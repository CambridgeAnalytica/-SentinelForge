import { test, expect } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";

// Valid test credentials — must match DEFAULT_ADMIN_USERNAME / DEFAULT_ADMIN_PASSWORD
const VALID_USER = process.env.TEST_USERNAME ?? "sf_admin";
const VALID_PASS = process.env.TEST_PASSWORD ?? "SentinelForge!2026";

const IS_CI = !!process.env.CI;

test.describe("Auth Flow", () => {
    test("login page renders correctly", async ({ page }) => {
        await page.goto(`${BASE_URL}/login`);

        // Branding
        await expect(page.locator("h1")).toContainText("SentinelForge");

        // Form fields
        await expect(page.locator("#username")).toBeVisible();
        await expect(page.locator("#password")).toBeVisible();

        // Submit button
        await expect(
            page.locator("button[type='submit']")
        ).toContainText("Sign in");
    });

    test("invalid credentials show error message", async ({ page }) => {
        test.skip(IS_CI, "Requires running API server");
        await page.goto(`${BASE_URL}/login`);

        await page.fill("#username", "bad_user");
        await page.fill("#password", "bad_password");
        await page.locator("button[type='submit']").click();

        // Error message should appear
        await expect(
            page.locator("text=Invalid credentials")
        ).toBeVisible({ timeout: 5000 });

        // Should stay on login page
        expect(page.url()).toContain("/login");
    });

    test("successful login redirects to dashboard", async ({ page }) => {
        test.skip(IS_CI, "Requires running API server");
        await page.goto(`${BASE_URL}/login`);

        await page.fill("#username", VALID_USER);
        await page.fill("#password", VALID_PASS);
        await page.locator("button[type='submit']").click();

        // Should redirect away from login
        await page.waitForURL((url) => !url.pathname.includes("/login"), {
            timeout: 10000,
        });

        // Dashboard heading should be visible
        await expect(page.locator("h2")).toBeVisible({ timeout: 5000 });
    });

    test("unauthenticated user sees no sidebar navigation", async ({ page }) => {
        // Clear any stored tokens
        await page.goto(`${BASE_URL}/login`);
        await page.evaluate(() => localStorage.clear());

        // Navigate to a protected page
        await page.goto(BASE_URL);

        // ClientShell renders without sidebar when not authenticated
        await expect(page.locator("nav")).not.toBeVisible({ timeout: 5000 });
    });

    test("sidebar navigation visible after login", async ({ page }) => {
        test.skip(IS_CI, "Requires running API server");
        await page.goto(`${BASE_URL}/login`);
        await page.fill("#username", VALID_USER);
        await page.fill("#password", VALID_PASS);
        await page.locator("button[type='submit']").click();

        await page.waitForURL((url) => !url.pathname.includes("/login"), {
            timeout: 10000,
        });

        // Sidebar nav items should be present
        await expect(page.locator("nav")).toBeVisible({ timeout: 5000 });
        await expect(page.locator("text=Dashboard")).toBeVisible();
        await expect(page.locator("text=Compliance")).toBeVisible();
        await expect(page.locator("text=Audit Log")).toBeVisible();
    });
});
