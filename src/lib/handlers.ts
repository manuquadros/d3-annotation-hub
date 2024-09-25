import {
    resources,
    sameClass,
    isStrain,
    isBacteria,
    isOrganism,
    isEnzyme,
} from "$lib/resources.ts";
import type { Resource } from "$lib/resources.ts";
import { trimRange } from "$lib/ranges.ts";
import { optionsDropdown, removeDropdown } from "$lib/dropdown";
import { newSpan, spanWrappedButton, annotateRange } from "$lib/utils";
import { get } from "svelte/store";

let selectedText = "";
let selectedSpan: HTMLSpanElement | null = null;
let sourceRes: Resource | null;
let targetRes: Resource | null;

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

export function handleKeyPress(event: KeyboardEvent) {
    if (/[Aa]/.test(event.key)) {
        handleTextSelection(event);
    }
}

export function handleSpanClick(event: MouseEvent) {
    console.log(get(resources));
    console.log("click");
    // const target = event.target as HTMLElement;
    // if (target.classList.contains("entity")) {
    //     event.stopPropagation();
    //     selectedSpan = target as HTMLSpanElement;
    //     showRemoveDropdown = true;
    //     showDropdown = false;
    //     dropdownPosition = { x: event.clientX, y: event.clientY };
    //     setOptionsDropdown(event);
    // } else {
    //     showRemoveDropdown = false;
    // }
}

export function handleOptionClick(option: string): void {
    const selection = window.getSelection();
    if (selection && !selection.isCollapsed) {
        const range = trimRange(selection.getRangeAt(0));
        const label = `d3o:${option}`;

        annotateRange(label, range);
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
