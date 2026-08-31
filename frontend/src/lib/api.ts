import { apiUrl } from "@/lib/env";

/**
 * Thin fetch wrapper for calling the Django backend. Always builds the
 * request URL from `apiUrl` (sourced from NEXT_PUBLIC_API_URL) — never
 * hardcode the backend origin in a component.
 */
export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = new URL(path, apiUrl);
  return fetch(url, init);
}
