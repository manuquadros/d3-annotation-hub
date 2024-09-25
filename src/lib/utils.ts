import {
    dragStart,
    dragOver,
    handleDrop,
    handleSpanClick,
} from "$lib/handlers.ts";
import { resources } from "$lib/resources.ts";

const outOfScope = "OOS";

function isValidEntitySpan(span: HTMLSpanElement): boolean {
    const label = span.getAttribute("typeof");
    return span.getAttribute("resource") && label && label !== outOfScope;
}

export function processTags(content: HTMLDivElement): HTMLDivElement {
    const spans = content.querySelectorAll("span");

    spans.forEach((span) => {
        if (isValidEntitySpan(span)) {
            span = spanWrappedButton(span);
            resources.storeEntitySpan(span);
        }
    });

    return content;
}

export function spanWrappedButton(span: HTMLSpanElement): HTMLSpanElement {
    const button = createButton(
        span.className,
        span.getAttribute("typeof") as string,
    );

    return wrapButton(span, button);
}

function createButton(
    className: string,
    label: string,
    draggable: boolean = false,
): HTMLButtonElement {
    const button = document.createElement("button");

    button.className = className;
    button.setAttribute("typeof", label);
    button.type = "button";
    if (draggable) {
        button.draggable = true;
        button.addEventListener("dragstart", dragStart);
        button.addEventListener("dragover", dragOver);
        button.addEventListener("drop", handleDrop);
    }
    button.addEventListener("click", handleSpanClick);

    return button;
}

function wrapButton(parent: Element, button: HTMLButtonElement): Element {
    button.textContent = parent.textContent;
    parent.textContent = "";
    parent.appendChild(button);
    return parent;
}
