import { SaveSequencer } from "./saveSequencer";

export type SequencedPage<B> =
    | { status: "ok"; data: B }
    | { status: "superseded" }
    | { status: "error" };

/**
 * Fetches one page of a filtered/paginated list through a {@link SaveSequencer}
 * so a slower earlier request can never overwrite a newer one. The sequencer
 * aborts any prior in-flight request and marks it stale; this returns
 * `superseded` (never the parsed body) whenever a newer load has begun — either
 * by the abort landing before the response, or by the staleness check after it —
 * so the caller leaves the currently-displayed page in place. `error` covers a
 * non-OK response or a failed fetch; `ok` carries the parsed body.
 *
 * The sequencer must be owned by the caller (one per independently-paged table)
 * and reused across that table's loads, since sharing one sequencer is what ties
 * successive requests into a single "latest wins" sequence.
 */
export async function loadSequencedPage<B>(
    sequencer: SaveSequencer,
    url: string,
): Promise<SequencedPage<B>> {
    const { signal, isCurrent } = sequencer.begin();
    try {
        const res = await fetch(url, { signal });
        if (!isCurrent()) return { status: "superseded" };
        if (!res.ok) return { status: "error" };
        const data = (await res.json()) as B;
        if (!isCurrent()) return { status: "superseded" };
        return { status: "ok", data };
    } catch (err) {
        if (err instanceof Error && err.name === "AbortError")
            return { status: "superseded" };
        return { status: "error" };
    }
}
