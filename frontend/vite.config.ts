import { sveltekit } from "@sveltejs/kit/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig } from "vitest/config";

export default defineConfig({
    plugins: [sveltekit(), svelteTesting()],
    test: {
        environment: "jsdom",
        globals: true,
        slowTestThreshold: 1,
        bail: 1,
        coverage: {
            enabled: true,
            provider: "v8",
        },
    },
});
