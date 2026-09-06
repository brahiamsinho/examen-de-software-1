import { apiUrl } from "@/lib/env";

/**
 * Credentialed, CSRF-aware transport seam for the Django Ninja backend
 * (design.md DD1/DD2). Nothing below this module knows about cookies or
 * CSRF; nothing above it calls `fetch` directly — every domain client
 * (`lib/auth.ts`, `lib/organizations.ts`) goes through `apiFetch`.
 */

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const CSRF_COOKIE_NAME = "csrftoken";
const CSRF_HEADER_NAME = "X-CSRFToken";
const CSRF_ENDPOINT = "/api/auth/csrf";

export type ApiFetchInit = Omit<RequestInit, "credentials"> & { json?: unknown };

type ApiErrorPayload = {
  status: number;
  code: string;
  detail: string;
};

/** A response arrived but signalled failure (non-2xx). */
export class ApiError extends Error {
  status: number;
  code: string;
  detail: string;

  constructor({ status, code, detail }: ApiErrorPayload) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

/** No response arrived at all (offline, DNS failure, CORS rejection, ...). */
export class NetworkError extends Error {
  constructor(message = "Network request failed") {
    super(message);
    this.name = "NetworkError";
  }
}

let cachedCsrfToken: string | null = null;

export function invalidateCsrfToken(): void {
  cachedCsrfToken = null;
}

function readCsrfCookie(): string | null {
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${CSRF_COOKIE_NAME}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]!) : null;
}

/** Unconditionally fetches a fresh token from the backend, ignoring any
 * existing cookie or cache. Used both for the initial priming call and for
 * the single re-prime that follows a stale-token 403. */
async function primeCsrfToken(): Promise<string> {
  const url = new URL(CSRF_ENDPOINT, apiUrl);
  const response = await fetch(url, { credentials: "include" });

  if (!response.ok) {
    throw new NetworkError("Failed to prime CSRF token");
  }

  const body = (await response.json()) as { csrf_token: string };
  cachedCsrfToken = body.csrf_token;
  return cachedCsrfToken;
}

/**
 * Cookie fast path → module cache → body-token priming call (design.md
 * DD2). The cookie fast path covers local dev, where the frontend and
 * backend share `localhost`; the body-token path covers the deployed
 * cross-domain matrix, where JS on the app domain cannot read the API
 * domain's cookie.
 */
export async function csrfToken(): Promise<string> {
  const cookieToken = readCsrfCookie();
  if (cookieToken) {
    return cookieToken;
  }
  if (cachedCsrfToken) {
    return cachedCsrfToken;
  }
  return primeCsrfToken();
}

function isUnsafeMethod(method: string | undefined): boolean {
  return UNSAFE_METHODS.has((method ?? "GET").toUpperCase());
}

async function toApiError(response: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  const record =
    body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  const code = typeof record.code === "string" ? record.code : `http_${response.status}`;
  const rawDetail = record.detail;
  const detail = typeof rawDetail === "string" ? rawDetail : JSON.stringify(rawDetail ?? null);

  return new ApiError({ status: response.status, code, detail });
}

async function performRequest<T>(path: string, init: ApiFetchInit): Promise<T> {
  const { json, ...rest } = init;
  const unsafe = isUnsafeMethod(rest.method);
  const headers = new Headers(rest.headers);

  let body = rest.body;
  if (json !== undefined) {
    body = JSON.stringify(json);
    if (!headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
  }

  if (unsafe) {
    headers.set(CSRF_HEADER_NAME, await csrfToken());
  }

  const url = new URL(path, apiUrl);
  const send = () => fetch(url, { ...rest, body, headers, credentials: "include" });

  let response: Response;
  try {
    response = await send();
  } catch {
    throw new NetworkError();
  }

  // Exactly one re-prime + retry on a stale-token 403 (design.md DD2) — no
  // loop. The retry deliberately uses the token `primeCsrfToken()` just
  // returned rather than going back through `csrfToken()`'s cookie-first
  // check: a stale `csrftoken` cookie would otherwise win again and the
  // retry would fail identically.
  if (unsafe && response.status === 403) {
    invalidateCsrfToken();
    headers.set(CSRF_HEADER_NAME, await primeCsrfToken());
    try {
      response = await send();
    } catch {
      throw new NetworkError();
    }
  }

  if (!response.ok) {
    throw await toApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/**
 * `credentials: "include"` is set internally and cannot be overridden via
 * `init` (the `Omit<RequestInit, "credentials">` type). A forgotten
 * `credentials` option becomes a silent anonymous request instead of a
 * test failure — this seam makes that class of bug unrepresentable.
 */
export async function apiFetch<T>(path: string, init: ApiFetchInit = {}): Promise<T> {
  return performRequest<T>(path, init);
}
