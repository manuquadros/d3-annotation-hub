import {
    dragStart,
    dragOver,
    handleDrop,
    handleSpanClick,
} from "$lib/handlers.ts";
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
    const name = span.textContent;

    new ChunkButton({
        target: span,
        props: { key, label, name },
        hydrate: true,
    });

    return span;
}

export function createButton(
    className: string,
    label: string,
    draggable: boolean = false,
    name: string,
): HTMLButtonElement {
    const button = document.createElement("button");

    button.type = "button";
    if (draggable) {
        button.draggable = true;
        button.addEventListener("dragstart", dragStart);
        button.addEventListener("dragover", dragOver);
        button.addEventListener("drop", handleDrop);
    }

    button.className = className;
    button.setAttribute("typeof", label);
    button.textContent = name;
    button.addEventListener("click", handleSpanClick);

    return button;
}

export function wrapRange(range: Range, resource: Resource): HTMLSpanElement {
    const span = newSpan(resource.label, rangeToClass(range, "entity"));
    span.setAttribute("resource", resource.name);
    range.surroundContents(span);
    spanWrappedButton(span);

    return span;
}
