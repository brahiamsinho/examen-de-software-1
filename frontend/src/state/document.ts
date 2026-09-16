import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import {
  getDocument as getDocumentApi,
  openDocumentSocket,
  submitCommand as submitCommandApi,
  type CommandResult,
  type UmlCommandIn,
  type UmlDocument,
} from "@/lib/uml_documents";

/** Mirrors `DiagramCanvas`'s local `LockState` structurally (DD9, DD12). */
export type LockState = { ownerLabel: string; mine: boolean };

/** Client throttle for `node.position` (DD4): 20 Hz, well above the ~12 Hz
 * fusion threshold for perceived-continuous motion, and a third of a raw
 * 60 Hz `mousemove` stream. */
const _POSITION_THROTTLE_MS = 50;

/** Close codes DD13 treats as terminal — a revoked or unauthenticated
 * client must never hammer the handshake in a reconnect loop. */
const _TERMINAL_CLOSE_CODES = new Set([4401, 4403, 4404]);
const _INITIAL_BACKOFF_MS = 1000;
const _MAX_BACKOFF_MS = 10_000;

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
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [trackedKey, setTrackedKey] = useState(`${orgSlug}:${docId}`);
  // Low-frequency (DD11) — genuinely belongs in render, unlike live
  // positions below.
  const [locks, setLocks] = useState<Record<string, LockState>>({});

  const connectionRef = useRef<ReturnType<typeof openDocumentSocket> | null>(null);
  // Live positions bypass React state entirely (DD11): `DiagramCanvas`
  // writes its imperative Cytoscape-apply handler into this ref on mount,
  // and the socket's `node.position` handler below calls through it
  // directly — a `setState` at 20 Hz per dragger would re-render the whole
  // page for data only Cytoscape consumes.
  const positionListenerRef = useRef<((classId: string, x: number, y: number) => void) | null>(null);
  // Same ref-as-latest-handler idiom (DD12): a claim loss is rare, but the
  // snap-back is still an imperative "restore this exact node's position"
  // action, not a state change anything else in the tree reads.
  const claimRejectedListenerRef = useRef<((classId: string) => void) | null>(null);
  const positionThrottleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingPositionRef = useRef<{ classId: string; x: number; y: number } | null>(null);

  const key = `${orgSlug}:${docId}`;
  if (key !== trackedKey) {
    setTrackedKey(key);
    setDocument(null);
    setError(null);
    setLastValidation(null);
    setLoading(orgSlug !== null);
    setLocks({});
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
   * Realtime socket effect (design.md DD11/DD13), independent of the
   * fetch-on-mount effect above (its own refetch on open is deliberately
   * redundant — the monotonic merge below bails out on an equal revision,
   * so it costs nothing). Reconnects with capped exponential backoff
   * (1s→2s→4s→8s→10s) on any non-terminal close; `4401`/`4403`/`4404` are
   * terminal, so a revoked or unauthenticated client never hammers the
   * handshake in a loop.
   */
  useEffect(() => {
    if (orgSlug === null) return;

    let cancelled = false;
    let socket: ReturnType<typeof openDocumentSocket> | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let backoffMs = _INITIAL_BACKOFF_MS;

    const mergeRemote = (incoming: UmlDocument) => {
      setDocument((prev) => (prev !== null && incoming.revision <= prev.revision ? prev : incoming));
    };

    const connect = () => {
      socket = openDocumentSocket(orgSlug, docId, {
        onOpen: () => {
          backoffMs = _INITIAL_BACKOFF_MS;
          getDocumentApi(orgSlug, docId)
            .then((fetched) => {
              if (!cancelled) mergeRemote(fetched);
            })
            .catch(() => {
              // A refetch failure on open is not fatal: the socket stays
              // open and later broadcasts still arrive.
            });
        },
        onMessage: (incoming) => {
          if (!cancelled) mergeRemote(incoming);
        },
        onClose: (event) => {
          if (cancelled || _TERMINAL_CLOSE_CODES.has(event.code)) return;
          const delay = backoffMs;
          backoffMs = Math.min(backoffMs * 2, _MAX_BACKOFF_MS);
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
          }, delay);
        },
        onNodeLocked: (payload) => {
          if (cancelled) return;
          setLocks((prev) => ({
            ...prev,
            [payload.class_id]: { ownerLabel: payload.owner_label, mine: payload.mine },
          }));
        },
        onNodeUnlocked: (payload) => {
          if (cancelled) return;
          setLocks((prev) => {
            if (!(payload.class_id in prev)) return prev;
            const next = { ...prev };
            delete next[payload.class_id];
            return next;
          });
        },
        onNodeLocks: (payload) => {
          if (cancelled) return;
          const next: Record<string, LockState> = {};
          for (const entry of payload.locks) {
            next[entry.class_id] = { ownerLabel: entry.owner_label, mine: entry.mine };
          }
          setLocks(next);
        },
        onNodePosition: (payload) => {
          // The owner's own drag already renders locally in real time
          // (DD9) — only a foreign frame needs to move anything here.
          if (cancelled || payload.mine) return;
          positionListenerRef.current?.(payload.class_id, payload.x, payload.y);
        },
        onClaimRejected: (payload) => {
          if (cancelled) return;
          claimRejectedListenerRef.current?.(payload.class_id);
        },
      });
      connectionRef.current = socket;
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer !== null) clearTimeout(reconnectTimer);
      socket?.close();
      connectionRef.current = null;
    };
  }, [orgSlug, docId]);

  const sendClaim = useCallback((classId: string) => {
    connectionRef.current?.sendClaim(classId);
  }, []);

  const sendRelease = useCallback((classId: string, x: number | null, y: number | null) => {
    connectionRef.current?.sendRelease(classId, x, y);
  }, []);

  /**
   * Throttled `node.position` sender (design.md DD4, Testing Strategy):
   * leading-edge send is immediate, then further calls within the same
   * 50ms window are coalesced into "pending" and flushed exactly once at
   * the trailing edge — so at most one frame goes out per window, and the
   * very last coalesced position is never silently dropped.
   */
  const sendPosition = useCallback((classId: string, x: number, y: number) => {
    // A plain local recursive closure, not another hook value: the
    // trailing edge re-schedules itself directly so this window keeps
    // flushing pending calls without `sendPosition` ever referencing its
    // own `useCallback` identity before it settles.
    const flushPending = () => {
      positionThrottleTimerRef.current = null;
      const pending = pendingPositionRef.current;
      pendingPositionRef.current = null;
      if (pending) {
        connectionRef.current?.sendPosition(pending.classId, pending.x, pending.y);
        positionThrottleTimerRef.current = setTimeout(flushPending, _POSITION_THROTTLE_MS);
      }
    };

    if (positionThrottleTimerRef.current === null) {
      connectionRef.current?.sendPosition(classId, x, y);
      positionThrottleTimerRef.current = setTimeout(flushPending, _POSITION_THROTTLE_MS);
    } else {
      pendingPositionRef.current = { classId, x, y };
    }
  }, []);

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
   *
   * `isSubmitting` is set before the POST starts and cleared in a `finally`
   * (success or failure), so every command-submitting control can share one
   * cross-control lock instead of each relying only on its own local
   * `submitting` state — two commands fired from two different controls in
   * close succession could otherwise race their `getDocument` refetches and
   * leave the render transiently reflecting only one command's effect
   * (post-verify WARNING 3 on uml-canvas-remove-ui).
   */
  const submitCommand = useCallback(
    async (command: UmlCommandIn) => {
      if (orgSlug === null) throw new Error("No active organization");
      setIsSubmitting(true);
      try {
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
      } finally {
        setIsSubmitting(false);
      }
    },
    [orgSlug, docId],
  );

  return {
    document,
    loading,
    error,
    lastValidation,
    isSubmitting,
    submitCommand,
    locks,
    positionListenerRef,
    claimRejectedListenerRef,
    sendClaim,
    sendPosition,
    sendRelease,
  };
}
