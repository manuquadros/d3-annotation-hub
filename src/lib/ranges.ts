/**
 * Compute a class name for a new annotation, depending on whether it ends at a
 * word boundary or nor.
 * @param range A Range object
 * @param prefix A basic class name to which the computed name is appended.
 */
export function rangeToClass(range: Range, prefix: string = "entity"): string {
    const startText = range.startContainer.textContent;
    const endText = range.endContainer.textContent;
    const start = range.startOffset;
    const end = range.endOffset;

    let classLabel = prefix;
    let space = " ";
    if (!classLabel) {
        space = "";
    }

    if (startText && !containsSpace(startText, start - 1, start + 1)) {
        classLabel += space + "in-word-left";
    }

    if (endText && !containsSpace(endText, end, end + 1)) {
        classLabel += space + "in-word-right";
    }

    return classLabel;
}

function containsSpace(text: string, start: number, end: number): boolean {
    return /\s/.test(text.slice(start, end));
}

export function trimRange(range: Range): Range {
    const text = range.toString();

    for (let i = 0; i < text.length && /\s/.test(text[i]); i++) {
        range.setStart(range.startContainer, range.startOffset + 1);
    }

    for (let i = text.length - 1; i >= 0 && /\s/.test(text[i]); i--) {
        range.setEnd(range.endContainer, range.endOffset - 1);
    }

    return range;
}
