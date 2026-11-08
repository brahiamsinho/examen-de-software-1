"use client";

import { AlertCircle, Download, RefreshCw } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  describeEntry,
  kindLabel,
  userOptions,
  type LogEntry,
  type LogFilters,
  type LogSession,
} from "@/lib/session_log";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entries: LogEntry[];
  sessions: LogSession[];
  filters: LogFilters;
  loading: boolean;
  error: string | null;
  exporting: boolean;
  exportError: string | null;
  onFiltersChange: (filters: LogFilters) => void;
  onExport: () => void;
  onReload: () => void;
};

const formatTime = (iso: string) =>
  new Date(iso).toLocaleString("es", { dateStyle: "short", timeStyle: "short" });

function sessionLabel(session: LogSession): string {
  const period =
    session.started_at === session.ended_at
      ? formatTime(session.started_at)
      : `${formatTime(session.started_at)} – ${formatTime(session.ended_at)}`;
  return `Sesión ${session.session} · ${period} (${session.entries})`;
}

/**
 * Presentational view of the diagram's session log: filters by session and by
 * user, the entries (who, what, when) and a CSV export of what is on screen.
 * The container owns the loading and the download. The log is read-only: this
 * dialog has no way to edit an entry.
 */
export function ActivityLogDialog({
  open,
  onOpenChange,
  entries,
  sessions,
  filters,
  loading,
  error,
  exporting,
  exportError,
  onFiltersChange,
  onExport,
  onReload,
}: Props) {
  function setSession(value: string) {
    const next: LogFilters = { ...filters };
    if (value === "") delete next.session;
    else next.session = Number(value);
    onFiltersChange(next);
  }

  function setUser(value: string) {
    const next: LogFilters = { ...filters };
    if (value === "") delete next.user;
    else next.user = value;
    onFiltersChange(next);
  }

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Bitácora"
      description="Solo los miembros de la organización pueden ver la bitácora. Incluye los cambios de personas y de la IA, las decisiones sobre sus propuestas y los mensajes del chat. Los registros no se pueden editar."
      className="max-w-3xl"
    >
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-48 flex-1 flex-col gap-1.5">
          <Label htmlFor="log-session">Sesión</Label>
          <Select id="log-session" value={filters.session === undefined ? "" : String(filters.session)} onChange={(event) => setSession(event.target.value)}>
            <option value="">Todas las sesiones</option>
            {sessions.map((session) => (
              <option key={session.session} value={String(session.session)}>
                {sessionLabel(session)}
              </option>
            ))}
          </Select>
        </div>
        <div className="flex min-w-40 flex-1 flex-col gap-1.5">
          <Label htmlFor="log-user">Usuario</Label>
          <Select id="log-user" value={filters.user ?? ""} onChange={(event) => setUser(event.target.value)}>
            <option value="">Todos los usuarios</option>
            {userOptions(sessions).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </div>
        <Button type="button" variant="outline" onClick={onReload}>
          <RefreshCw />
          Actualizar
        </Button>
        <Button type="button" onClick={onExport} disabled={exporting}>
          <Download />
          {exporting ? "Exportando..." : "Exportar CSV"}
        </Button>
      </div>

      {exportError ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{exportError}</AlertDescription>
        </Alert>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : loading ? (
        <p className="text-sm text-muted-foreground">Cargando bitácora...</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted-foreground">Todavía no hay registros con estos filtros.</p>
      ) : (
        <ul className="flex max-h-96 flex-col gap-2 overflow-y-auto pr-1" aria-label="Registros de la bitácora">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className={`flex flex-col gap-0.5 rounded-lg border px-3 py-2 text-sm ${
                entry.is_ai ? "border-violet-500/30 bg-violet-500/10" : "border-border bg-muted/40"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <time dateTime={entry.created_at}>{formatTime(entry.created_at)}</time>
                <span>Sesión {entry.session}</span>
                <span className="rounded-full border border-border px-2 py-0.5">{kindLabel(entry.kind)}</span>
                <span className={`font-semibold ${entry.is_ai ? "text-violet-600" : "text-foreground"}`}>
                  {entry.author}
                </span>
              </div>
              <p className="whitespace-pre-wrap break-words">{describeEntry(entry)}</p>
            </li>
          ))}
        </ul>
      )}
    </Dialog>
  );
}
