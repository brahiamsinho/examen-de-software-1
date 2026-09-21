import { atom, useAtomValue, useSetAtom } from "jotai";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { createDocument, listDocuments, type DocumentSummary } from "@/lib/uml_documents";
import { importXmi, stashImportWarnings } from "@/lib/xmi_interop";

/**
 * Bumped after any mutation that changes the document list (create, import,
 * rename). The list is read by two siblings under `(app)/layout.tsx` — the
 * sidebar and the dashboard grid — so a counter both hooks depend on is the
 * cheapest way to keep them fresh without a shared cache: every mounted
 * `useDocuments` refetches when it changes, so a stale sidebar can never
 * outlive a mutation.
 */
const documentsVersionAtom = atom(0);

export function useInvalidateDocuments() {
  const setVersion = useSetAtom(documentsVersionAtom);
  return useCallback(() => setVersion((v) => v + 1), [setVersion]);
}

/**
 * The two "new diagram" entry points (sidebar "+" and the dashboard header)
 * share one behavior: call the API, invalidate the shared list, open the new
 * diagram. A failure rethrows so the calling form can show its own error.
 */
export function useDocumentActions(orgSlug: string | null) {
  const router = useRouter();
  const invalidate = useInvalidateDocuments();

  const createDiagram = useCallback(
    async (input: { name: string }) => {
      const doc = await createDocument(orgSlug!, input);
      invalidate();
      router.push(`/documents/${doc.id}`);
      return doc;
    },
    [orgSlug, invalidate, router],
  );

  const importDiagram = useCallback(
    async (file: File) => {
      const doc = await importXmi(orgSlug!, file);
      stashImportWarnings(doc.id, doc.warnings);
      invalidate();
      router.push(`/documents/${doc.id}`);
    },
    [orgSlug, invalidate, router],
  );

  return { createDiagram, importDiagram };
}

/**
 * Local `useState` keyed by `orgSlug` (design.md DD5), plus the shared
 * `documentsVersionAtom` so a mutation elsewhere refetches every mounted
 * instance. Idle while `orgSlug` is null; the loading flag only covers the
 * first fetch per org — a version-triggered refetch keeps the current list on
 * screen instead of flashing a skeleton.
 */
export function useDocuments(orgSlug: string | null) {
  const version = useAtomValue(documentsVersionAtom);
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
  }, [orgSlug, version]);

  return { documents, loading, error };
}
