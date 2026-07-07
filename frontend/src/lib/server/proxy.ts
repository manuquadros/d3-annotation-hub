import type { RequestEvent } from "@sveltejs/kit";
import { API_BASE_URL } from "$lib/config";

/** Time-to-first-byte budget for an upstream call; 0 disables it. */
const DEFAULT_TIMEOUT_MS = 30_000;

/**
 * Hop-by-hop / connection headers must not be re-emitted, and the backend must
 * never set cookies on the SvelteKit domain — the auth cookie is owned solely by
 * the login route.
 */
const STRIPPED_RESPONSE_HEADERS = new Set([
    "connection",
    "keep-alive",
    "transfer-encoding",
    "content-encoding",
    "content-length",
    "set-cookie",
]);

export type QueryValue = string | number | boolean | undefined | null;

export interface ProxyOptions {
    method?: string;
    body?: BodyInit | null;
    /** Extra request headers (e.g. Content-Type). Authorization is added automatically. */
    headers?: Record<string, string>;
    /** Query params; `undefined`/`null` values are dropped, the rest URL-encoded. */
    query?: Record<string, QueryValue>;
    /** Time-to-first-byte budget in ms; 0 disables. Defaults to 30s. */
    timeoutMs?: number;
}

/**
 * Tagged template that percent-encodes each interpolated value as a single path
 * segment while leaving the literal parts (and their slashes) untouched.
 *
 * This is the choke point that stops a `%2F`/`..` in a route param from
 * redirecting a token-bearing proxied request onto a different backend path or
 * method than the route implies.
 *
 * @example backendPath`/projects/${id}/queue` // `id` is encoded, the slashes are not
 */
export function backendPath(
    strings: TemplateStringsArray,
    ...values: Array<string | number>
): string {
    let out = strings[0];
    for (let i = 0; i < values.length; i++) {
        out += encodeURIComponent(String(values[i])) + strings[i + 1];
    }
    return out;
}

/**
 * Forward an authenticated request to the backend. Reads the `auth_token`
 * cookie (401 when absent), attaches the Bearer token, builds the query string
 * safely, bounds the time-to-first-byte, and returns a status-preserving,
 * header-filtered streaming response.
 *
 * `path` must already be a safe backend path — build it with the `backendPath`
 * tagged template whenever it embeds route params.
 */
export async function proxy(
    event: RequestEvent,
    path: string,
    options: ProxyOptions = {},
): Promise<Response> {
    const token = event.cookies.get("auth_token");
    if (!token) return new Response(null, { status: 401 });

    let url = `${API_BASE_URL}${path}`;
    if (options.query) {
        const qs = new URLSearchParams();
        for (const [key, value] of Object.entries(options.query)) {
            if (value !== undefined && value !== null) {
                qs.set(key, String(value));
            }
        }
        const suffix = qs.toString();
        if (suffix) url += `?${suffix}`;
    }

    const headers: Record<string, string> = {
        Authorization: `Bearer ${token}`,
        ...options.headers,
    };

    const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
    const controller = timeoutMs > 0 ? new AbortController() : null;
    const timer = controller
        ? setTimeout(() => controller.abort(), timeoutMs)
        : null;

    let upstream: Response;
    try {
        upstream = await fetch(url, {
            method: options.method ?? "GET",
            headers,
            body: options.body ?? null,
            signal: controller?.signal,
        });
    } catch (err) {
        if (timer) clearTimeout(timer);
        const timedOut = err instanceof Error && err.name === "AbortError";
        return new Response(
            timedOut ? "Upstream timed out" : "Upstream request failed",
            { status: timedOut ? 504 : 502 },
        );
    }
    // Headers are in; a streamed body (e.g. the SSE ontology import) may still
    // take minutes, so stop the TTFB guard now rather than aborting mid-stream.
    if (timer) clearTimeout(timer);

    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
        if (!STRIPPED_RESPONSE_HEADERS.has(key.toLowerCase())) {
            responseHeaders.set(key, value);
        }
    });

    return new Response(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: responseHeaders,
    });
}
