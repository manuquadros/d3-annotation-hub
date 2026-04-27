import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
    testDir: "./e2e",
    retries: 0,
    workers: 1,
    reporter: "list",
    use: {
        baseURL: "http://localhost:5173",
        trace: "retain-on-failure",
    },
    projects: [
        {
            name: "setup",
            testMatch: /auth\.setup\.ts/,
        },
        {
            name: "chromium",
            use: {
                ...devices["Desktop Chrome"],
                storageState: "e2e/.auth.json",
            },
            dependencies: ["setup"],
        },
    ],
    webServer: {
        command: "pnpm dev",
        url: "http://localhost:5173",
        reuseExistingServer: true,
    },
});
