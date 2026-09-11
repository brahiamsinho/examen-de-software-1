import { atom, useAtom } from "jotai";
import { useEffect } from "react";

import { ApiError } from "@/lib/api";
import { fetchMe, type User } from "@/lib/auth";

/**
 * Session state as a discriminated union (design.md DD5). Makes "an outage
 * logs the user out" unrepresentable rather than merely untested — a 401
 * `ApiError` means anonymous, but a `NetworkError` or any other `ApiError`
 * means the check itself failed, not that the user is signed out.
 */
export type SessionState =
  | { status: "loading" }
  | { status: "authenticated"; user: User }
  | { status: "anonymous" }
  | { status: "error"; message: string };

/**
 * Exported so `LoginForm`/`RegisterForm` can write the freshly authenticated
 * user directly after a successful call, instead of forcing a redundant
 * `fetchMe()` round trip (mirrors DD7's optimistic-update principle).
 */
export const sessionAtom = atom<SessionState>({ status: "loading" });

/**
 * Session-only dismiss flag for `VerifyEmailBanner` (design.md DD6). A
 * plain atom, never `atomWithStorage`/`localStorage`: the active-org key in
 * `state/organizations.ts` is a *preference* that must survive reload, but
 * a verification reminder is a *nag* that should return next session until
 * resolved — persisting it would also re-introduce that module's documented
 * SSR hydration-mismatch problem.
 */
export const verifyBannerDismissedAtom = atom(false);

/** Fires `fetchMe()` once per mount; owns the single source of truth for
 * whether the current visitor is authenticated. */
export function useSession(): SessionState {
  const [session, setSession] = useAtom(sessionAtom);

  useEffect(() => {
    let cancelled = false;

    fetchMe()
      .then((user) => {
        if (!cancelled) setSession({ status: "authenticated", user });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof ApiError && error.status === 401) {
          setSession({ status: "anonymous" });
        } else {
          const message = error instanceof Error ? error.message : "Unknown error";
          setSession({ status: "error", message });
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return session;
}
