import {
    dragStart,
    dragOver,
    handleDrop,
    handleSpanClick,
} from "$lib/handlers.ts";
import { resources } from "$lib/resources.ts";
import { get } from "svelte/store";
import { rangeToClass } from "$lib/ranges.ts";

const outOfScope = "OOS";

export function isValidEntitySpan(span: HTMLSpanElement): boolean {
    const label = span.getAttribute("typeof");
    return span.getAttribute("resource") && label && label !== outOfScope;
}

export function newSpan(label: string, className: string) {
    const span = document.createElement("span");
    span.className = className;
    span.setAttribute("typeof", label);

    return span;
}

export function spanWrappedButton(span: HTMLSpanElement): HTMLSpanElement {
    const button = createButton(
        span.className,
        span.getAttribute("typeof") as string,
    );

    return wrapButton(span, button);
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

function wrapButton(parent: Element, button: HTMLButtonElement): Element {
    button.textContent = parent.textContent;
    parent.textContent = "";
    parent.appendChild(button);
    return parent;
}

export function wrapRange(range: Range, resource: Resource): HTMLSpanElement {
    const span = newSpan(resource.label, rangeToClass(range, "entity"));
    span.setAttribute("resource", resource.name);
    range.surroundContents(span);
    spanWrappedButton(span);

    return span;
}
