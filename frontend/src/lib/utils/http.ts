/**
 * Extract a human-readable error message from a failed `fetch` Response.
 *
 * Reads the body once as text, then prefers a JSON `detail` field (the
 * FastAPI convention). Falls back to the raw body text when it isn't JSON —
 * so a 502/HTML gateway page or a SvelteKit proxy failure is surfaced rather
 * than swallowed into a generic status message — and finally to the status
 * line when the body is empty.
 */
export async function errorDetail(res: Response): Promise<string> {
    const text = await res.text().catch(() => "");
    if (text) {
        try {
            const body = JSON.parse(text);
            if (body && typeof body.detail === "string") {
                return body.detail;
            }
        } catch {
            // Not JSON — surface the raw text below.
        }
        return text;
    }
    return res.statusText || `Request failed (${res.status})`;
}
