"use client";

import { useEffect, useState } from "react";

import {
  listLog,
  listLogSessions,
  type LogEntry,
  type LogFilters,
  type LogSession,
} from "@/lib/session_log";

type Loaded = { key: string; entries: LogEntry[]; sessions: LogSession[]; error: string | null };

/**
 * Loads a diagram's session log while its dialog is open, and again whenever
 * the filters change or `reload()` is called. `loading` is derived (the data on
 * screen belongs to another request), so no state is set synchronously inside
 * the effect. Nothing is requested while the dialog is closed.
 */
export function useSessionLog(orgSlug: string | null, docId: string, open: boolean) {
  const [filters, setFilters] = useState<LogFilters>({});
  const [reloadToken, setReloadToken] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);

  const active = open && orgSlug !== null;
  const key = `${orgSlug}:${docId}:${JSON.stringify(filters)}:${reloadToken}`;

  useEffect(() => {
    if (!active || orgSlug === null) return;
    let cancelled = false;

    Promise.all([listLog(orgSlug, docId, filters), listLogSessions(orgSlug, docId)])
      .then(([entries, sessions]) => {
        if (!cancelled) setLoaded({ key, entries, sessions, error: null });
      })
      .catch(() => {
        if (!cancelled) {
          setLoaded({ key, entries: [], sessions: [], error: "No se pudo cargar la bitácora. Intenta de nuevo." });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [active, orgSlug, docId, filters, key]);

  return {
    entries: loaded?.entries ?? [],
    sessions: loaded?.sessions ?? [],
    error: loaded?.key === key ? loaded.error : null,
    loading: active && loaded?.key !== key,
    filters,
    setFilters,
    reload: () => setReloadToken((token) => token + 1),
  };
}
