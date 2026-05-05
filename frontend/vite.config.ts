import { execSync } from "child_process";
import { sveltekit } from "@sveltejs/kit/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig } from "vitest/config";

function appVersion(): string {
    try {
        return execSync("git describe --tags --always", { encoding: "utf8" }).trim();
    } catch {
        return "dev";
    }
}

export default defineConfig({
    plugins: [sveltekit(), svelteTesting()],
    define: {
        __APP_VERSION__: JSON.stringify(appVersion()),
    },
    test: {
        include: ["src/**/*.spec.ts"],
        environment: "jsdom",
        globals: true,
        bail: 1,
        coverage: {
            provider: "v8",
        },
    },
});
