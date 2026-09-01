import globals from "globals";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";
import tsdoc from "eslint-plugin-tsdoc";
import svelte from "eslint-plugin-svelte";

/** @type {import('eslint').Linter.Config[]} */
export default [
    {
        ignores: [
            "static/digidive/",
            ".svelte-kit/",
            "coverage/",
            "build/",
            "src/lib/api.generated.d.ts",
        ],
    },
    {
        files: ["**/*.ts"],
        plugins: { tsdoc },
        rules: { "tsdoc/syntax": "warn" },
    },
    { languageOptions: { globals: globals.browser } },
    pluginJs.configs.recommended,
    ...tseslint.configs.recommended,
    ...svelte.configs["flat/recommended"],
    {
        files: ["**/*.svelte", "**/*.svelte.ts", "**/*.svelte.js"],
        languageOptions: {
            parserOptions: { parser: tseslint.parser },
        },
        rules: {
            // No base path is configured, so resolveRoute() adds no value.
            "svelte/no-navigation-without-resolve": "off",
            // Flags Map/Set used as local computation variables inside $derived.by(),
            // which don't need SvelteMap/SvelteSet.
            "svelte/prefer-svelte-reactivity": "off",
            "@typescript-eslint/no-unused-vars": [
                "error",
                {
                    varsIgnorePattern: "^_",
                    argsIgnorePattern: "^_",
                },
            ],
        },
    },
    {
        files: ["**/*.ts"],
        rules: {
            "svelte/no-navigation-without-resolve": "off",
            "@typescript-eslint/no-unused-vars": [
                "error",
                {
                    varsIgnorePattern: "^_",
                    argsIgnorePattern: "^_",
                },
            ],
        },
    },
];
