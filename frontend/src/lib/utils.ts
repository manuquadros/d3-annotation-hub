import { rangeToClass } from "$lib/ranges.ts";

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


