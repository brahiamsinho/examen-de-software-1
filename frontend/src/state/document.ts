import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  getDocument as getDocumentApi,
  submitCommand as submitCommandApi,
  type CommandResult,
  type UmlCommandIn,
  type UmlDocument,
} from "@/lib/uml_documents";

/**
 * Distinguishes a genuine 404 (`ApiError` with `status === 404`) from any
 * other load failure, so the container can render "not found" only for the
 * former and a distinct generic message otherwise (post-verify WARNING 2).
 */
export type DocumentError = { message: string; notFound: boolean };

/**
 * Runtime shape guard for a resolved `submitCommand` response. `apiFetch`
 * casts the response body to `CommandResult` with no schema validation, so a
 * 200 OK with a missing/malformed `validation` field would otherwise flow
 * straight into state and crash `ValidationPanel` (post-verify CRITICAL 2).
 */
function isValidCommandResult(value: unknown): value is CommandResult {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  if (typeof candidate.revision !== "number") return false;
  const validation = candidate.validation;
  if (typeof validation !== "object" || validation === null) return false;
  return Array.isArray((validation as Record<string, unknown>).violations);
}

/**
 * Local `useState`, not a Jotai atom (design.md DD2): exactly one consumer
 * (the `[docId]` container) and it must reset per document — a module atom
 * would paint document A's classes for a frame after navigating to B. Uses
 * the same render-time tracked-key reset that `useMembers` uses for
 * `orgSlug`, satisfying `react-hooks/set-state-in-effect`, but keyed on
 * `${orgSlug}:${docId}` since either one changing must reset state here.
 */
export function useDocument(orgSlug: string | null, docId: string) {
  const [document, setDocument] = useState<UmlDocument | null>(null);
  const [loading, setLoading] = useState(orgSlug !== null);
  const [error, setError] = useState<DocumentError | null>(null);
  const [lastValidation, setLastValidation] = useState<CommandResult["validation"] | null>(null);
  const [trackedKey, setTrackedKey] = useState(`${orgSlug}:${docId}`);

  const key = `${orgSlug}:${docId}`;
  if (key !== trackedKey) {
    setTrackedKey(key);
    setDocument(null);
    setError(null);
    setLastValidation(null);
    setLoading(orgSlug !== null);
  }

  useEffect(() => {
    if (orgSlug === null) return;

    let cancelled = false;

    getDocumentApi(orgSlug, docId)
      .then((fetched) => {
        if (!cancelled) setDocument(fetched);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError({
            message: err instanceof Error ? err.message : "Unknown error",
            notFound: err instanceof ApiError && err.status === 404,
          });
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orgSlug, docId]);

  /**
   * POSTs, then `await getDocument(...)` and writes both the refetched
   * document and the returned `CommandResultOut.validation` into state
   * before resolving (DD3). The POST's `revision` is *not* used to patch
   * state — the GET is the single source. A rejected POST leaves
   * `document` untouched and rethrows.
   *
   * A resolved-but-malformed POST body is rejected before touching state at
   * all (CRITICAL 2). If the POST succeeds but the follow-up GET rejects,
   * the already-applied server-side validation is still stored (WARNING 1)
   * before surfacing a distinct, non-generic error to the caller.
   */
  const submitCommand = useCallback(
    async (command: UmlCommandIn) => {
      if (orgSlug === null) throw new Error("No active organization");
      const result = await submitCommandApi(orgSlug, docId, command);

      if (!isValidCommandResult(result)) {
        throw new Error("La respuesta del servidor tiene un formato inesperado.");
      }

      try {
        setDocument(await getDocumentApi(orgSlug, docId));
      } catch {
        setLastValidation(result.validation);
        throw new Error(
          "El comando se aplicó pero no se pudo actualizar la vista. Recargá la página.",
        );
      }

      setLastValidation(result.validation);
      return result;
    },
    [orgSlug, docId],
  );

  return { document, loading, error, lastValidation, submitCommand };
}
