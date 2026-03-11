import { rangeToClass } from "$lib/ranges.ts";
import { Map } from "immutable";

import type { Resource } from "./resources.svelte.ts";

export const outOfScope = "OOS";
let currID = 1;

export function entID(): number {
    return currID++;
}

export function isValidEntitySpan(span: HTMLSpanElement): boolean {
    const label = span.getAttribute("typeof");
    const resid = span.getAttribute("resource");
    return (
        label !== null &&
        label !== outOfScope &&
        resid !== null &&
        span.textContent !== null
    );
}

export function newSpan(
    label: string,
    className: string,
    resource: string,
): HTMLSpanElement {
    const span = document.createElement("span");
    span.className = className;
    span.setAttribute("typeof", label);
    span.setAttribute("resource", resource);
    span.id = String(entID());

    return span;
}

export function wrapRange(range: Range, resource: Resource): HTMLSpanElement {
    const span = newSpan(
        resource.label,
        rangeToClass(range, "entity"),
        resource.resourceid,
    );
    range.surroundContents(span);

    return span;
}

export function getContrastColor(hexColor: string | undefined): string {
    // Return default if no color provided
    if (!hexColor) return "#000000";

    // Remove # if present
    const hex = hexColor.replace("#", "");

    // Parse RGB values
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;

    // Convert to linear RGB
    const toLinear = (c: number) =>
        c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    const rLinear = toLinear(r);
    const gLinear = toLinear(g);
    const bLinear = toLinear(b);

    // Calculate relative luminance (WCAG formula)
    const luminance = 0.2126 * rLinear + 0.7152 * gLinear + 0.0722 * bLinear;

    // Return black for light backgrounds, white for dark backgrounds
    return luminance > 0.179 ? "#000000" : "#ffffff";
}

export function getLabelColor(label: string): string | undefined {
    const labelColors = Map([
        ["d3o:Strain", "#ECAF00"],
        ["d3o:Bacteria", "#B61F29"],
        ["d3o:Enzyme", "#000064"],
    ]);

    return labelColors.get(label) ?? "#CCCCCC"; // Return gray as fallback
}
