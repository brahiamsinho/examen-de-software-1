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
        "frontend/.env.local (or set it in your deployment environment) " +
        "and point it at wherever the Django API is reachable.",
    );
  }

  return value;
}

export const apiUrl = readApiUrl();
