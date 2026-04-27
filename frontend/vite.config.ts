import { sveltekit } from "@sveltejs/kit/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
    plugins: [sveltekit(), svelteTesting()],
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
