import {
    resources,
    sameClass,
    isStrain,
    isBacteria,
    isOrganism,
    isEnzyme,
} from "$lib/resources.ts";
import type { Resource } from "$lib/resources.ts";
import { relations } from "$lib/relations.ts";
import { trimRange } from "$lib/ranges.ts";
import { optionsDropdown, removeDropdown } from "$lib/dropdown";
import { newSpan, spanWrappedButton } from "$lib/utils";
import { annotateRange } from "$lib/body";

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
    if (selection && !selection.isCollapsed) {
        if (body && body.contains(selection.anchorNode.parentNode)) {
            selectedText = selection.toString().trim();
            if (selectedText) {
                setOptionsDropdown(event);
            }
        }
    } else {
        optionsDropdown.hide();
    }
}

export function handleKeyPress(event: KeyboardEvent) {
    if (/[Aa]/.test(event.key)) {
        handleTextSelection(event);
    }
}

export function handleSpanClick(event: MouseEvent) {
    const target = event.target as Element;
    if (target.classList.contains("entity")) {
        event.stopPropagation();
        selectedSpan = target as Element;
        removeDropdown.show();
        optionsDropdown.hide();
        removeDropdown.position(event.clientX, event.clientY);
    } else {
        removeDropdown.hide();
    }
}

export function handleOptionClick(option: string): void {
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) {
        const range = trimRange(selection.getRangeAt(0));
        const label = `d3o:${option}`;

        const { resource } = annotateRange(label, range);
        selection.removeAllRanges();
    }
    optionsDropdown.hide();
}

export function handleRemoveAnnotation() {
    if (selectedSpan) {
        const parent = selectedSpan.parentNode;
        removeEntitySpan(selectedSpan);
        if (parent) {
            while (selectedSpan.firstChild) {
                parent.insertBefore(selectedSpan.firstChild, selectedSpan);
            }
            parent.removeChild(selectedSpan);
        }
    }
    showRemoveDropdown = false;
}

export function handleDrop(e: DragEvent): void {
    const sourceRes = e.dataTransfer.getData("text/plain");
    const targetRes = resourceFromTarget(e.target);
    if (sourceRes && targetRes) {
        if (sameClass(sourceRes, targetRes)) {
            resources.merge(sourceRes, targetRes);
        } else if (isStrain(sourceRes) && isBacteria(targetRes)) {
            relations.add(sourceRes, "d3o:hasSpecies", targetRes);
        } else if (isBacteria(sourceRes) && isStrain(targetRes)) {
            relations.add(targetRes, "d3o:hasSpecies", sourceRes);
        } else if (isEnzyme(sourceRes) && isOrganism(targetRes)) {
            relations.add(targetRes, "d3o:hasEnzyme", sourceRes);
        } else if (isOrganism(sourceRes) && isEnzyme(targetRes)) {
            relations.add(sourceRes, "d3o:hasEnzyme", targetRes);
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
    return null;
}

export function getOptions(): Array<string> {
    const options: Array<string> = [];
    if (sourceRes && targetRes) {
        if (isStrain(sourceRes) && isBacteria(targetRes)) {
            options.push("is strain of");
        }
        if (isBacteria(sourceRes) && isStrain(targetRes)) {
            options.push("is superordinate of");
        }
        if (isEnzyme(sourceRes) && isOrganism(targetRes)) {
            options.push("is found in");
        }
        if (isOrganism(sourceRes) && isEnzyme(targetRes)) {
            options.push("has");
        }
    }
    return options;
}

export function dragStart(e: DragEvent): void {
    e.dataTransfer.clearData();
    e.dataTransfer.setData("text/plain", resourceFromTarget(e.target));
}

export function dragOver(e: DragEvent): void {
    e.preventDefault();
}
