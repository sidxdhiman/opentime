import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest";
import {
  http,
  HttpError,
  statusMessage,
  errorMessage,
  onUnauthorized,
  reportUnauthorized,
} from "./http";

function jsonResponse(status: number, body: unknown, headers?: Record<string, string>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

const originalFetch = globalThis.fetch;

beforeAll(() => {
  globalThis.fetch = vi.fn() as unknown as typeof fetch;
});

afterEach(() => {
  vi.clearAllMocks();
});

afterAll(() => {
  globalThis.fetch = originalFetch;
});

describe("statusMessage", () => {
  it("never labels a missing resource (404) as a server error", () => {
    expect(statusMessage(404, "something")).toContain("couldn't be found");
    expect(statusMessage(404, "something").toLowerCase()).not.toContain("server");
  });

  it("distinguishes auth/forbidden/rate-limit/server failures", () => {
    expect(statusMessage(401)).toContain("session");
    expect(statusMessage(403).toLowerCase()).toContain("permission");
    expect(statusMessage(429).toLowerCase()).toContain("too many requests");
    expect(statusMessage(500).toLowerCase()).toContain("our end");
    expect(statusMessage(503).toLowerCase()).toContain("our end");
  });

  it("ignores backend detail entirely (no leak)", () => {
    const secret = "mongo uri: mongodb://internal:27017";
    expect(statusMessage(500, secret)).not.toContain("mongodb");
    expect(statusMessage(500, secret)).not.toContain("internal");
  });
});

describe("errorMessage", () => {
  it("normalizes unknown/plain errors to a safe generic message", () => {
    expect(errorMessage("boom")).toBe("Something went wrong. Please try again.");
    expect(errorMessage(new Error("raw backend internals"))).toBe(
      "Something went wrong. Please try again.",
    );
  });

  it("preserves HttpError sanitized messages", () => {
    const err = new HttpError(404, statusMessage(404), "not_found");
    expect(errorMessage(err)).toBe(err.message);
  });
});

describe("http", () => {
  it("returns JSON on success and undefined on 204", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse(200, { ok: true }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(http("/ok", { timeoutMs: 1000 })).resolves.toEqual({ ok: true });
    await expect(http("/no-content", { timeoutMs: 1000 })).resolves.toBeUndefined();
  });

  it("throws HttpError carrying status but never leaking backend detail", async () => {
    const leaked = "sql trace: SELECT * FROM secrets";
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse(500, { detail: leaked, code: "boom" }),
    );

    const err = (await http("/e", { timeoutMs: 1000 }).catch((e) => e)) as HttpError;
    expect(err).toBeInstanceOf(HttpError);
    expect(err.status).toBe(500);
    expect(err.code).toBe("boom");
    expect(err.message).not.toContain("sql");
    expect(err.message).not.toContain("SELECT");
  });

  it("notifies global 401 subscribers once and reports status 401", async () => {
    const listener = vi.fn();
    const off = onUnauthorized(listener);
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(401, { detail: "expired" }));

    await expect(http("/authz", { timeoutMs: 1000 })).rejects.toMatchObject({
      status: 401,
    });
    expect(listener).toHaveBeenCalledTimes(1);
    off();
  });

  it("removes a listener after unsubscribe", async () => {
    const listener = vi.fn();
    const off = onUnauthorized(listener);
    off();
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(401, {}));
    await http("/x", { timeoutMs: 1000 }).catch(() => {});
    expect(listener).not.toHaveBeenCalled();
  });

  it("reportUnauthorized triggers subscribers directly", async () => {
    const listener = vi.fn();
    const off = onUnauthorized(listener);
    reportUnauthorized();
    expect(listener).toHaveBeenCalledTimes(1);
    off();
  });

  it("times out a hung request and returns control with a retriable timeout", async () => {
    // Mock fetch that stays pending until the passed signal aborts (mirroring
    // real fetch abort semantics), then rejects with AbortError.
    vi.mocked(fetch).mockImplementationOnce(
      (input, init) =>
        new Promise<Response>((_resolve, reject) => {
          const signal = init?.signal;
          if (signal?.aborted) {
            reject(new DOMException("aborted", "AbortError"));
            return;
          }
          signal?.addEventListener(
            "abort",
            () => reject(new DOMException("aborted", "AbortError")),
            { once: true },
          );
        }),
    );

    const err = (await http("/slow", { timeoutMs: 50 }).catch((e) => e)) as HttpError;
    expect(err).toBeInstanceOf(HttpError);
    expect(err.status).toBe(0);
    expect(err.code).toBe("timeout");
    expect(err.retriable).toBe(true);
  }, 5000);

  it("rethrows the caller's own abort (unmount) unchanged", async () => {
    const controller = new AbortController();
    vi.mocked(fetch).mockImplementationOnce(
      () =>
        new Promise((_resolve, reject) => {
          controller.signal.addEventListener("abort", () =>
            reject(new DOMException("aborted", "AbortError")),
          );
        }) as Promise<Response>,
    );

    setTimeout(() => controller.abort(), 20);
    await expect(http("/abortme", { signal: controller.signal })).rejects.toThrow(
      DOMException,
    );
  });

  it("maps network failure to a retriable network error", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const err = (await http("/offline", { timeoutMs: 1000 }).catch((e) => e)) as HttpError;
    expect(err).toBeInstanceOf(HttpError);
    expect(err.code).toBe("network");
    expect(err.retriable).toBe(true);
  });

  it("maps a sanitized status message for 404 responses", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(404, { detail: "Genesis memory not found" }));
    const err = (await http("/genesis", { timeoutMs: 1000 }).catch((e) => e)) as HttpError;
    expect(err).toBeInstanceOf(HttpError);
    expect(err.status).toBe(404);
    expect(err.message).toContain("couldn't be found");
    expect(err.message).not.toContain("Genesis memory not found");
  });
});
