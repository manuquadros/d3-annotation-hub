export type EvidenceParagraph = { excerptHtml: string; fullHtml: string; isExcerpt: boolean };
export type Span = [number, number];
export type PointerItem = { offset: number; length: number };

function escapeHtml(s: string): string {
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}

export function splitSentences(text: string): Array<{ start: number; end: number }> {
    const result: Array<{ start: number; end: number }> = [];
    let start = 0;
    for (let i = 0; i < text.length; i++) {
        if (/[.!?]/.test(text[i])) {
            let end = i + 1;
            while (end < text.length && /[.!?'")\]»]/.test(text[end])) end++;
            if (end >= text.length || (text[end] === " " && end + 1 < text.length && /[A-Z]/.test(text[end + 1]))) {
                result.push({ start, end });
                start = end + 1;
                i = end;
            }
        }
    }
    if (start < text.length) result.push({ start, end: text.length });
    return result.length > 0 ? result : [{ start: 0, end: text.length }];
}

export function findMinSentenceWindow(
    sentences: Array<{ start: number; end: number }>,
    subjSpans: Span[],
    objSpans: Span[],
): { startIdx: number; endIdx: number } {
    const hasSubj = sentences.map(({ start, end }) =>
        subjSpans.some(([s, e]) => s < end && e > start),
    );
    const hasObj = sentences.map(({ start, end }) =>
        objSpans.some(([s, e]) => s < end && e > start),
    );

    let bestStart = 0;
    let bestEnd = sentences.length - 1;
    let found = false;
    let left = 0;
    let sc = 0;
    let oc = 0;

    for (let right = 0; right < sentences.length; right++) {
        if (hasSubj[right]) sc++;
        if (hasObj[right]) oc++;
        while (sc > 0 && oc > 0) {
            if (!found || right - left < bestEnd - bestStart) {
                bestStart = left;
                bestEnd = right;
                found = true;
            }
            if (hasSubj[left]) sc--;
            if (hasObj[left]) oc--;
            left++;
        }
    }
    return { startIdx: bestStart, endIdx: bestEnd };
}

export function buildSegmentHtml(
    text: string,
    subjSpans: Span[],
    objSpans: Span[],
    subjBg: string,
    objBg: string,
    subjFg: string,
    objFg: string,
): string {
    type Mark = [number, number, string, string];
    const marks: Mark[] = [
        ...subjSpans.map(([s, e]) => [s, e, subjBg, subjFg] as Mark),
        ...objSpans.map(([s, e]) => [s, e, objBg, objFg] as Mark),
    ].sort((a, b) => a[0] - b[0]);

    let result = "";
    let cursor = 0;
    for (const [start, end, bg, fg] of marks) {
        if (start >= cursor) {
            result += escapeHtml(text.slice(cursor, start));
            const spanEnd = Math.max(end, start + 1);
            result += `<mark style="background-color:${bg};color:${fg};border-radius:2px;padding:0 2px">${escapeHtml(text.slice(start, spanEnd))}</mark>`;
            cursor = spanEnd;
        }
    }
    result += escapeHtml(text.slice(cursor));
    return result;
}

/**
 * Returns {start, end} character ranges (into body.textContent) for every
 * paragraph-level element. Uses the Range API so the offsets match the
 * pointer offsets stored in the database (both are into body.textContent).
 * Falls back to the whole body when no <p>/<li> elements are found.
 */
export function getParagraphRanges(doc: Document): Array<{ start: number; end: number }> {
    const body = doc.body;
    const paras = Array.from(body.querySelectorAll("p, li"));
    if (paras.length === 0) {
        return [{ start: 0, end: body.textContent?.length ?? 0 }];
    }
    return paras.map((el) => {
        const r = doc.createRange();
        r.setStart(body, 0);
        r.setEndBefore(el);
        const start = r.toString().length;
        const end = start + (el.textContent?.length ?? 0);
        return { start, end };
    });
}

export function buildEvidenceParagraphs(
    plainText: string,
    paraRanges: Array<{ start: number; end: number }>,
    subjectPointers: PointerItem[],
    objectPointers: PointerItem[],
    subjBg: string,
    objBg: string,
    subjFg: string,
    objFg: string,
): EvidenceParagraph[] {
    const result: EvidenceParagraph[] = [];

    for (const { start, end } of paraRanges) {
        const subjSpans: Span[] = [];
        const objSpans: Span[] = [];

        for (const p of subjectPointers) {
            if (p.offset >= start && p.offset < end) {
                subjSpans.push([p.offset - start, p.offset - start + p.length]);
            }
        }
        for (const p of objectPointers) {
            if (p.offset >= start && p.offset < end) {
                objSpans.push([p.offset - start, p.offset - start + p.length]);
            }
        }

        if (subjSpans.length === 0 || objSpans.length === 0) continue;

        const text = plainText.slice(start, end).trim();
        if (!text) continue;

        const fullHtml = buildSegmentHtml(text, subjSpans, objSpans, subjBg, objBg, subjFg, objFg);

        const sentences = splitSentences(text);
        const { startIdx, endIdx } = findMinSentenceWindow(sentences, subjSpans, objSpans);
        const isExcerpt = startIdx > 0 || endIdx < sentences.length - 1;

        if (!isExcerpt) {
            result.push({ excerptHtml: fullHtml, fullHtml, isExcerpt: false });
        } else {
            const excerptStart = sentences[startIdx].start;
            const excerptEnd = sentences[endIdx].end;
            const excerptText = text.slice(excerptStart, excerptEnd);
            const adjustedSubj = subjSpans
                .filter(([s, e]) => s < excerptEnd && e > excerptStart)
                .map(([s, e]) => [Math.max(0, s - excerptStart), Math.min(excerptEnd - excerptStart, e - excerptStart)] as Span);
            const adjustedObj = objSpans
                .filter(([s, e]) => s < excerptEnd && e > excerptStart)
                .map(([s, e]) => [Math.max(0, s - excerptStart), Math.min(excerptEnd - excerptStart, e - excerptStart)] as Span);
            const excerptHtml = buildSegmentHtml(excerptText, adjustedSubj, adjustedObj, subjBg, objBg, subjFg, objFg);
            result.push({ excerptHtml, fullHtml, isExcerpt: true });
        }
    }

    return result;
}
