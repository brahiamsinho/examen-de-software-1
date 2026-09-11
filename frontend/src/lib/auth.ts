import { apiFetch, invalidateCsrfToken } from "@/lib/api";

/**
 * Domain client for `apps/users` (design.md's `lib/auth.ts` — one module
 * per backend Django app). No cookie/CSRF knowledge here; everything goes
 * through `apiFetch`.
 */

export type User = {
  id: string;
  email: string;
  full_name: string;
  is_verified: boolean;
};

export type MessageResponse = { message: string };

export async function register(input: {
  email: string;
  password: string;
  full_name?: string;
}): Promise<User> {
  return apiFetch<User>("/api/auth/register", { method: "POST", json: input });
}

export async function login(input: { email: string; password: string }): Promise<User> {
  const user = await apiFetch<User>("/api/auth/login", { method: "POST", json: input });
  // Django rotates the CSRF token on login; drop the cached value so the
  // next unsafe request re-primes instead of sending a stale token.
  invalidateCsrfToken();
  return user;
}

export async function logout(): Promise<void> {
  await apiFetch<void>("/api/auth/logout", { method: "POST" });
  // Django rotates the CSRF token on logout too.
  invalidateCsrfToken();
}

export async function fetchMe(): Promise<User> {
  return apiFetch<User>("/api/auth/me");
}

export async function verifyEmail(input: { token: string }): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/auth/verify-email", { method: "POST", json: input });
}

export async function resendVerification(): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/auth/resend-verification", { method: "POST" });
}

export async function requestPasswordReset(input: { email: string }): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/auth/password-reset/request", {
    method: "POST",
    json: input,
  });
}

export async function confirmPasswordReset(input: {
  token: string;
  password: string;
}): Promise<MessageResponse> {
  return apiFetch<MessageResponse>("/api/auth/password-reset/confirm", {
    method: "POST",
    json: input,
  });
}
