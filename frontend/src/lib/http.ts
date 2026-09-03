/**
 * Shared HTTP foundation for the OpenTime frontend.
 *
 * Guarantees:
 *  - Every failure carries the HTTP status so callers can distinguish
 *    auth (401), forbidden (403), missing (404), rate-limit (429) and
 *    server (5xx) failures — and maps missing resources to a clear
 *    "not found" message instead of a generic server error.
 *  - Raw backend `detail` strings are NEVER propagated to user-facing
 *    surfaces. Each status maps to a stable, human-readable message.
 *  - Global 401 (session-expired) awareness: any 401 notifies subscribers
 *    (e.g. the auth provider) so the whole app can clear an expired
 *    session in one place, closing cross-user/expired-session gaps.
 *  - Optional timeout and abort support so hung requests return control.
 */

export class HttpError extends Error {
  constructor(
    public status: number,
    message: string,
    public code?: string,
    public retriable = false,
  ) {
    super(message);
    this.name = "HttpError";
  }
}

/** Timeout + abort helpers --- a non-2xx status is converted to HttpError. */
export const DEFAULT_TIMEOUT_MS = 30_000;

export interface HttpOptions extends RequestInit {
  /** Override the default request timeout (ms). Pass 0 to disable. */
  timeoutMs?: number;
}

export function timeoutAbortSignal(timeoutMs: number): {
  signal: AbortSignal;
  timer: ReturnType<typeof setTimeout>;
} {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return { signal: controller.signal, timer };
}

/**
 * Map an HTTP status (and any backend-provided detail) to a stable,
 * human-readable message. Backend `detail` is deliberately never used.
 */
export function statusMessage(status: number, _detail?: unknown): string {
  if (status === 400) return "That request couldn't be processed. Please check and try again.";
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 403) return "You don't have permission to do that.";
  if (status === 404) return "That item couldn't be found. It may have been removed.";
  if (status === 409) return "That change conflicts with the current state. Please refresh and try again.";
  if (status === 429) return "Too many requests — please wait a moment and try again.";
  if (status === 422) return "Some of the information provided isn't valid. Please check and try again.";
  if (status >= 500) return "Something went wrong on our end. Please try again.";
  return "That request didn't go through. Please try again.";
}

/** A fetch that timed out/aborted by us (not by the caller). */
export function isTimeout(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/**
 * Stable, human-readable message for any thrown error. Never leaks raw
 * backend detail; unknown/plain errors fall back to a generic message.
 */
export function errorMessage(e: unknown): string {
  if (e instanceof HttpError) return e.message;
  if (e instanceof DOMException && e.name === "AbortError") {
    return "That request was cancelled.";
  }
  return "Something went wrong. Please try again.";
}

type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

/** Subscribe to global 401-session-expiry events (e.g. the auth provider). */
export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => unauthorizedListeners.delete(listener);
}

function notifyUnauthorized(): void {
  unauthorizedListeners.forEach((l) => {
    try {
      l();
    } catch {
      /* never let a listener break session handling */
    }
  });
}

/**
 * Core authenticated JSON request. Throws `HttpError` with a sanitized
 * message (never backend detail). Honors caller aborts and an optional
 * timeout. On a 401, notifies global session-expiry listeners exactly once.
 */
export async function http<T>(
  url: string,
  options: HttpOptions = {},
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = options;
  const callerSignal = rest.signal ?? undefined;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let timeoutController: AbortController | null = null;

  let signal: AbortSignal | undefined = callerSignal;
  let onCallerAbort: (() => void) | undefined;

  if (timeoutMs > 0 && !callerSignal) {
    timeoutController = new AbortController();
    timer = setTimeout(() => timeoutController!.abort(), timeoutMs);
    signal = timeoutController!.signal;
  } else if (timeoutMs > 0 && callerSignal) {
    // Combine caller abort with a timeout into a single signal.
    timeoutController = new AbortController();
    signal = timeoutController!.signal;
    const passAbort = () => timeoutController!.abort();
    if (callerSignal.aborted) passAbort();
    else callerSignal.addEventListener("abort", passAbort, { once: true });
    onCallerAbort = passAbort;
    timer = setTimeout(passAbort, timeoutMs);
  }

  let res: Response;
  try {
    res = await fetch(url, { ...rest, signal });
  } catch (e) {
    const callerAborted = callerSignal?.aborted;
    if (callerAborted) throw e;
    if (isTimeout(e) || timeoutController?.signal.aborted) {
      throw new HttpError(0, "That request took too long. Please try again.", "timeout", true);
    }
    throw new HttpError(0, "Couldn't reach the server. Check your connection and try again.", "network", true);
  } finally {
    if (timer) clearTimeout(timer);
    if (onCallerAbort) callerSignal?.removeEventListener("abort", onCallerAbort);
  }

  if (res.status === 401) {
    // Global session expiry — only the responder surfaces a durable state;
    // the auth provider reacts to the same event and clears the session.
    notifyUnauthorized();
    return Promise.reject(
      new HttpError(401, statusMessage(401), "unauthorized"),
    );
  }

  if (!res.ok) {
    let detail: unknown;
    try {
      detail = (await res.json()) as unknown;
    } catch {
      detail = undefined;
    }
    const code =
      detail && typeof detail === "object" && "code" in detail
        ? String((detail as { code?: unknown }).code)
        : undefined;
    throw new HttpError(res.status, statusMessage(res.status, detail), code);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

/** Report a 401 externally once (used by auth-refresh flows in api.ts). */
export function reportUnauthorized(): void {
  notifyUnauthorized();
}
