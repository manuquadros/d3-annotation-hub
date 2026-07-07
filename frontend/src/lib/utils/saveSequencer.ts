/**
 * A "latest wins" gate for overlapping async operations where only the newest
 * result may take effect — autosaves that replace the whole server-side record,
 * or filter/pagination loads that must not be overwritten by a slower earlier
 * request.
 *
 * When several operations overlap, an older (possibly retrying or just slow)
 * request can otherwise land after a newer one — overwriting a save with stale
 * data, or a table with results that no longer match the current filter. Each
 * operation calls {@link SaveSequencer.begin} to claim a token; the token aborts
 * any prior in-flight request and exposes `isCurrent()`, which is true only while
 * no newer operation has begun. Callers commit their result (and clear the
 * "saving"/"loading" state) only while `isCurrent()`, so superseded operations
 * become silent no-ops rather than stale overwrites or spurious errors.
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
