import { describe, test, expect } from "vitest";
import { findHardcodedColors, declaredRootTokens } from "../utils/cssAudit";

describe("findHardcodedColors", () => {
    test("accepts a block that names only design-system tokens", () => {
        const css = `
            .item {
                color: var(--primary-color);
                background: var(--tile-color);
                border: 1px solid var(--border-color);
            }
        `;

        expect(findHardcodedColors(css)).toEqual([]);
    });

    test("reports hex literals", () => {
        const css = ".a { color: #fff; border-color: #1a2b3c; }";

        expect(findHardcodedColors(css)).toEqual(["#fff", "#1a2b3c"]);
    });

    test("reports named colors, which the hex-only guard let through", () => {
        const css = ".a { color: red; background-color: white; }";

        expect(findHardcodedColors(css)).toEqual(["red", "white"]);
    });

    test("reports color functions other than a neutral rgba tint", () => {
        const css = `
            .a { color: hsl(0, 100%, 50%); }
            .b { background: rgb(1, 2, 3); }
            .c { background: rgba(255, 0, 0, 0.5); }
            .d { color: oklch(0.7 0.1 200); }
        `;

        expect(findHardcodedColors(css)).toEqual([
            "hsl(",
            "rgb(",
            "rgba(",
            "oklch(",
        ]);
    });

    test("keeps the translucent black shadow tints the components retain", () => {
        const css = `
            .a { box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12); }
            .b { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); }
            .c { box-shadow: inset 0 0 2px rgba(255, 255, 255, 0.4); }
        `;

        expect(findHardcodedColors(css)).toEqual([]);
    });

    test("reads no color out of a token name that ends in one", () => {
        const css = ".a { color: var(--red); background: var(--gray-color); }";

        expect(findHardcodedColors(css)).toEqual([]);
    });

    test("treats keywords and non-color values as clean", () => {
        const css = `
            .a {
                color: inherit;
                background: none;
                border-color: transparent;
                outline-color: currentcolor;
                text-decoration: none;
                transition: background-color 0.2s;
                padding: 0.45rem 0.7rem;
            }
        `;

        expect(findHardcodedColors(css)).toEqual([]);
    });

    test("ignores selectors and comments, which declare nothing", () => {
        const css = `
            /* red is fine in prose */
            .snow, .item[data-tone="gold"] { color: var(--muted-color); }
        `;

        expect(findHardcodedColors(css)).toEqual([]);
    });
});

describe("declaredRootTokens", () => {
    test("collects the custom properties declared on :root", () => {
        const css = "*:root { --primary-color: #06c; --tile-color: #fff; }";

        expect([...declaredRootTokens(css)]).toEqual([
            "--primary-color",
            "--tile-color",
        ]);
    });

    test("omits a property declared only inside a component rule", () => {
        const css = `
            :root { --primary-color: #06c; }
            body.sidebar-small { --sidebar-width: 4rem; }
        `;

        const tokens = declaredRootTokens(css);

        expect(tokens.has("--primary-color")).toBe(true);
        expect(tokens.has("--sidebar-width")).toBe(false);
    });
});
