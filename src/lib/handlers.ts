import {
    resources,
    sameClass,
    isStrain,
    isBacteria,
    isOrganism,
    isEnzyme,
} from "$lib/resources.ts";
import type { Resource } from "$lib/resources.ts";
import { rangeToClass, trimRange } from "../ranges.ts";
import { optionsDropdown, removeDropdown } from "$lib/dropdown";

let selectedText = "";
let selectedSpan: HTMLSpanElement | null = null;
let sourceRes: Resource | null;
let targetRes: Resource | null;

function processTags(element: HTMLElement): void {
    const spans = element.querySelectorAll("span[typeof]");

    spans.forEach((span) => {
        resources.storeEntitySpan(span);
    });
}

export function setOptionsDropdown(event: MouseEvent) {
    optionsDropdown.show();
    removeDropdown.hide();
    optionsDropdown.position(event.clientX, event.clientY);
}

export function handleTextSelection(event: Event) {
    const selection = window.getSelection();
    const body = document.querySelector("#chunk-body");
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

}

export function handleSpanClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (target.classList.contains("entity")) {
        event.stopPropagation();
        selectedSpan = target as HTMLSpanElement;
        showRemoveDropdown = true;
        showDropdown = false;
        dropdownPosition = { x: event.clientX, y: event.clientY };
        setOptionsDropdown(event);
    } else {
        showRemoveDropdown = false;
    }
}

export function handleOptionClick(option: string) {
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) {
        const range = trimRange(selection.getRangeAt(0));
        const span = document.createElement("span");
        const label = `d3o:${option}`;
        span.className = rangeToClass(range);
        span.setAttribute("typeof", label);
        range.surroundContents(span);
        selection.removeAllRanges();
        resources.storeEntitySpan(span);
    }
    showDropdown = false;
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
    targetRes = resourceFromTarget(e.target);
    if (sourceRes && targetRes) {
        if (sameClass(sourceRes, targetRes)) {
            resources.merge(sourceRes, targetRes);
        } else if (isStrain(sourceRes) && isBacteria(targetRes)) {
            relations.add(sourceRes, "strainOf", targetRes);
        } else if (isBacteria(sourceRes) && isStrain(targetRes)) {
            relations.add(targetRes, "strainOf", sourceRes);
        } else if (isEnzyme(sourceRes) && isOrganism(targetRes)) {
            relations.add(targetRes, "has", sourceRes);
        } else if (isOrganism(sourceRes) && isEnzyme(targetRes)) {
            relations.add(sourceRes, "has", targetRes);
        }
    }
}

function resourceFromTarget(target: EventTarget | null): Resource | null {
    if (target && target instanceof Element) {
        const id = target.getAttribute("resource");
        const label = target.getAttribute("typeof");

        if (id && label) {
            return { id: id, label: label };
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
    sourceRes = resourceFromTarget(e.target);
}

export function dragOver(e: DragEvent): void {
    e.preventDefault();
}
