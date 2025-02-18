import {
    sameClass,
    isStrain,
    isBacteria,
    isOrganism,
    isEnzyme,
} from "$lib/resources.svelte.ts";
import { trimRange } from "$lib/ranges.ts";
import { optionsDropdown, removeDropdown } from "$lib/dropdown";
import type { bodyStore } from "$lib/body.svelte.ts";
import { triple } from "./relations.svelte.ts";
import { get } from "svelte/store";

let selectedText = "";
let selectedSpan: HTMLSpanElement | null = null;

export function setOptionsDropdown(event: MouseEvent) {
    optionsDropdown.show();
    removeDropdown.hide();
    optionsDropdown.position(event.clientX, event.clientY);
}

export function handleTextSelection(event: Event) {
    const selection = window.getSelection();
    const body = document.querySelector("div.chunk-body");
    if (selection && selection.anchorNode && !selection.isCollapsed) {
        if (body && body.contains(selection.anchorNode.parentNode)) {
            selectedText = selection.toString().trim();
            if (selectedText) {
                setOptionsDropdown(event as MouseEvent);
            }
        }
    } else {
        optionsDropdown.hide();
    }
}

export function handleKeyPress(event: KeyboardEvent) {
    event.preventDefault();
    if (/[Aa]/.test(event.key)) {
        handleTextSelection(event);
    }
}

export function handleSpanClick(event: MouseEvent, body: bodyStore) {
    const target = event.target as Element;

    if (target.classList.contains("entity")) {
        event.stopPropagation();
        body.selectedSpan = target as HTMLSpanElement;
        removeDropdown.show();
        optionsDropdown.hide();
        removeDropdown.position(event.clientX, event.clientY);
    } else {
        removeDropdown.hide();
    }
}

export function handleOptionClick(option: string, context: bodyStore): void {
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) {
        const range = trimRange(selection.getRangeAt(0));
        const label = `d3o:${option}`;

        context.annotateRange(label, range);
        selection.removeAllRanges();
    }
    optionsDropdown.hide();
}

export function handleRemove(body: bodyStore) {
    const span = body.selectedSpan;

    if (span) {
        if (span.classList.contains("entitySummary")) {
            body.removeResource(span);
        } else {
            const parent = span.parentNode;

            if (parent) {
                while (span.firstChild) {
                    if (span.firstChild.nodeName === "BUTTON") {
                        while (span.firstChild.firstChild) {
                            parent.insertBefore(
                                span.firstChild.firstChild,
                                span,
                            );
                        }
                    }
                    parent.insertBefore(span.firstChild, span);
                }

                parent.removeChild(span);
            }
            parent?.removeChild(span);
        }
    }
    removeDropdown.hide();
}

export function handleDrop(e: DragEvent, context: bodyStore): void {
    const sourceRes = context.getResource(
        e.dataTransfer?.getData("text/plain") as string,
    );
    const targetRes = context.getResource(resourceFromTarget(e.target));
    const { relations } = context;
    if (sourceRes && targetRes) {
        if (sameClass(sourceRes, targetRes)) {
            context.mergeResources(sourceRes, targetRes);
        } else if (isStrain(sourceRes) && isBacteria(targetRes)) {
            relations.add(triple(sourceRes, "d3o:hasSpecies", targetRes));
        } else if (isBacteria(sourceRes) && isStrain(targetRes)) {
            relations.add(triple(targetRes, "d3o:hasSpecies", sourceRes));
        } else if (isBacteria(sourceRes) && isEnzyme(targetRes)) {
            relations.add(triple(sourceRes, "d3o:hasEnzyme", sourceRes));
        } else if (isEnzyme(sourceRes) && isOrganism(targetRes)) {
            relations.add(triple(targetRes, "d3o:hasEnzyme", sourceRes));
        } else if (isOrganism(sourceRes) && isEnzyme(targetRes)) {
            relations.add(triple(sourceRes, "d3o:hasEnzyme", targetRes));
        }
    }
}

function resourceFromTarget(target: EventTarget | null): string {
    if (target && target instanceof Element) {
        const id = target.getAttribute("resource");

        if (id) {
            return id;
        }
    }
    return "";
}

export function dragStart(e: DragEvent): void {
    e.dataTransfer?.clearData();
    e.dataTransfer?.setData("text/plain", resourceFromTarget(e.target));
}

export function dragOver(e: DragEvent): void {
    e.preventDefault();
}
