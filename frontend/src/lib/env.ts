/**
 * Central place to read environment-driven config for the frontend.
 *
 * No component should ever read `process.env.NEXT_PUBLIC_API_URL` (or
 * hardcode a backend URL) directly — import `apiUrl` from here instead.
 * Throwing at import time makes a missing/misconfigured environment fail
 * fast and loudly instead of silently breaking API calls at request time.
 */
function readApiUrl(): string {
  const value = process.env.NEXT_PUBLIC_API_URL;

  if (!value) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is not set. Copy frontend/env.local.example to " +
        "frontend/.env (or set it in your deployment environment) " +
        "and point it at wherever the Django API is reachable.",
    );
  }

  return value;
}

export const apiUrl = readApiUrl();

/**
 * Base URL the *Next.js server process* uses to reach the API. Inside the
 * frontend container `localhost` is the container itself, so a server-side
 * fetch to `apiUrl` would ECONNREFUSED; Compose sets INTERNAL_API_URL=
 * http://backend:8000. Falls back to `apiUrl` so bare `npm run dev` and
 * Vitest keep working unchanged.
 */
function readInternalApiUrl(): string {
  return process.env.INTERNAL_API_URL ?? apiUrl;
}

export const internalApiUrl = readInternalApiUrl();
