import {
    dragStart,
    dragOver,
    handleDrop,
    handleSpanClick,
} from "$lib/handlers.ts";
import { resources, outOfScope } from "$lib/resources.ts";

export function processTags(content: HTMLDivElement): HTMLDivElement {
    const spans = content.querySelectorAll("span[typeof]");

    spans.forEach((span) => {
        span = spanWrappedButton(span);
    });

    return content;
}

function spanWrappedButton(span: HTMLSpanElement): HTMLSpanElementxo {
    const label = span.getAttribute("typeof") as string;
    if (label !== outOfScope) {
        resources.storeEntitySpan(span);
        const button = createButton(
            span.className,
            span.getAttribute("typeof") as string,
        );
        span = wrapButton(span, button);
    }
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
