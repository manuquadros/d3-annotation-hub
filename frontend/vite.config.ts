import { execSync } from "child_process";
import { readFileSync } from "fs";
import { dirname, resolve } from "path";
import { fileURLToPath } from "url";
import { sveltekit } from "@sveltejs/kit/vite";
import { svelteTesting } from "@testing-library/svelte/vite";
import { defineConfig, type Plugin } from "vitest/config";
import { marked } from "marked";

const __dirname = dirname(fileURLToPath(import.meta.url));

function changelogPlugin(): Plugin {
    const virtualId = "virtual:changelog";
    const resolvedId = "\0" + virtualId;
    return {
        name: "vite-plugin-changelog",
        resolveId(id) {
            if (id === virtualId) return resolvedId;
        },
        load(id) {
            if (id !== resolvedId) return;
            let html: string;
            try {
                const md = readFileSync(resolve(__dirname, "../CHANGELOG.md"), "utf-8");
                html = marked.parse(md, { async: false });
            } catch (e) {
                console.warn("vite-plugin-changelog: could not read CHANGELOG.md", e);
                html = "<p>Changelog not available.</p>";
            }
            return `export const html = ${JSON.stringify(html)};`;
        },
    };
}

function appVersion(): string {
    try {
        return execSync("git describe --tags --always", { encoding: "utf8" }).trim();
    } catch {
        return "dev";
    }
}

export default defineConfig({
    plugins: [changelogPlugin(), sveltekit(), svelteTesting()],
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
