export function rangeToClass(range: Range, prefix: string = "entity"): string {
        const startText = range.startContainer.textContent;
        const endText = range.endContainer.textContent;
        const start = range.startOffset;
        const end = range.endOffset;

        let classLabel = prefix;

        if (startText && !/\s/.test(startText.slice(start - 1, start + 1))) {
                classLabel += " in-word-left";
        }

        if (endText && !/\s/.test(endText.slice(end, end + 1))) {
                classLabel += " in-word-right";
        }

        return classLabel;
}
