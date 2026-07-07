/**
 * A "latest wins" gate for autosaves that replace the whole server-side record.
 *
 * When several saves overlap, an older (possibly retrying or just slow) request
 * can otherwise land after a newer one and overwrite it with stale data. Each
 * save calls {@link SaveSequencer.begin} to claim a token; the token aborts any
 * prior in-flight request and exposes `isCurrent()`, which is true only while no
 * newer save has begun. Callers commit their result (and clear "saving" state)
 * only while `isCurrent()`, so superseded saves become silent no-ops rather than
 * stale overwrites or spurious errors.
 */
export class SaveSequencer {
    #seq = 0;
    #inFlight: AbortController | null = null;

    /**
     * Starts a new save, aborting the previous in-flight one. Returns the
     * `signal` to pass to `fetch` and `isCurrent()` to guard result handling.
     */
    begin(): { signal: AbortSignal; isCurrent: () => boolean } {
        this.#inFlight?.abort();
        const controller = new AbortController();
        this.#inFlight = controller;
        const seq = ++this.#seq;
        return {
            signal: controller.signal,
            isCurrent: () => seq === this.#seq,
        };
    }
}
