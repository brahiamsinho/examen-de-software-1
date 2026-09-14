import { useEffect, useState } from "react";

import { listDocuments, type DocumentSummary } from "@/lib/uml_documents";

/**
 * Local `useState`, not a Jotai atom (design.md DD5): a document list has
 * exactly one consumer (the dashboard container), the same condition under
 * which `state/document.ts` and `state/members.ts` both rejected a shared
 * atom. Idle while `orgSlug` is null; fetches on mount and refetches when
 * `orgSlug` changes. Read-only — no mutators, since `handleCreateDocument`
 * navigates away on success and there is nothing to append to.
 */
export function useDocuments(orgSlug: string | null) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(orgSlug !== null);
  const [error, setError] = useState<string | null>(null);
  const [trackedSlug, setTrackedSlug] = useState(orgSlug);

  /**
   * React's "adjusting state when a prop changes" pattern: reset
   * synchronously during render instead of inside the effect below, so
   * switching (or clearing) `orgSlug` never paints a stale list from the
   * previous org for a frame.
   */
  if (orgSlug !== trackedSlug) {
    setTrackedSlug(orgSlug);
    setDocuments([]);
    setError(null);
    setLoading(orgSlug !== null);
  }

  useEffect(() => {
    if (orgSlug === null) return;

    let cancelled = false;

    listDocuments(orgSlug)
      .then((fetched) => {
        if (!cancelled) setDocuments(fetched);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orgSlug]);

  return { documents, loading, error };
}
