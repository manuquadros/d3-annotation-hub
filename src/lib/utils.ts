import { rangeToClass } from "$lib/ranges.ts";

import ChunkButton from "$lib/components/ChunkButton.svelte";

export const outOfScope = "OOS";
let currID = 1;

export function entID(): number {
    return currID++;
}

export function isValidEntitySpan(span: HTMLSpanElement): boolean {
    const label = span.getAttribute("typeof");
    const resid = span.getAttribute("resource");
    return label !== outOfScope && resid !== null;
}

export function newSpan(label: string, className: string) {
    const span = document.createElement("span");
    span.className = className;
    span.setAttribute("typeof", label);
    span.id = String(entID());

    return span;
}

export function spanWrappedButton(span: HTMLSpanElement): HTMLSpanElement {
    const key = span.getAttribute("resource") as string;
    const label = span.getAttribute("typeof") as string;
    const name = span.textContent as string;
    span.textContent = "";

    new ChunkButton({
        target: span,
        props: { key, label, name },
    });

    return span;
}

export function wrapRange(range: Range, resource: Resource): HTMLSpanElement {
    const span = newSpan(resource.label, rangeToClass(range, "entity"));
    span.setAttribute("resource", resource.name);
    range.surroundContents(span);
    spanWrappedButton(span);

    return span;
}
