import { sveltekit } from "@sveltejs/kit/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig } from "vite";

export default defineConfig({
    plugins: [sveltekit(), svelteTesting()],
    test: {
        globals: true,
        slowTestThreshold: 1,
        bail: 1,
    },
});
