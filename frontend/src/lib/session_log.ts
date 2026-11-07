import { apiFetch, apiFetchBlob } from "@/lib/api";
import { saveBlobAsFile } from "@/lib/save_blob";

/**
 * Domain client for the per-diagram session log (`apps/session_log`, issue #17):
 * who did what in a diagram, people and AI, grouped into sessions. Read-only:
 * entries cannot be edited. Any member of the organization may read and export it.
 */
export type LogEntry = {
  id: number;
  /** Numbered per diagram; a new one starts after 30 minutes without activity. */
  session: number;
  kind: string;
  author: string;
  /** Null for the AI and for an account that was deleted. */
  author_id: string | null;
  is_ai: boolean;
  summary: string;
  data: Record<string, unknown>;
  created_at: string;
};

export type LogSession = {
  session: number;
  started_at: string;
  ended_at: string;
  entries: number;
  actors: { id: string | null; label: string; is_ai: boolean }[];
};

/** `user` is a user id or `"ai"`. */
export type LogFilters = { session?: number; user?: string };

const base = (orgSlug: string, docId: string) =>
  `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/log`;

export function logQuery(filters: LogFilters): string {
  const params = new URLSearchParams();
  if (filters.session !== undefined) params.set("session", String(filters.session));
  if (filters.user) params.set("user", filters.user);
  const text = params.toString().replaceAll("+", "%20");
  return text ? `?${text}` : "";
}

export function listLog(orgSlug: string, docId: string, filters: LogFilters): Promise<LogEntry[]> {
  return apiFetch<LogEntry[]>(`${base(orgSlug, docId)}${logQuery(filters)}`);
}

export function listLogSessions(orgSlug: string, docId: string): Promise<LogSession[]> {
  return apiFetch<LogSession[]>(`${base(orgSlug, docId)}/sessions`);
}

const FALLBACK_FILENAME = "bitacora.csv";

/** Downloads the CSV for the filters that are on screen. */
export async function downloadLog(orgSlug: string, docId: string, filters: LogFilters): Promise<void> {
  const { blob, filename } = await apiFetchBlob(`${base(orgSlug, docId)}/export${logQuery(filters)}`);
  saveBlobAsFile(blob, filename ?? FALLBACK_FILENAME);
}

const KIND_LABELS: Record<string, string> = {
  change: "Cambio",
  "chat.message": "Chat",
  "proposal.created": "Propuesta de la IA",
  "proposal.approved": "Aprobada",
  "proposal.rejected": "Rechazada",
  "version.restored": "Versión",
  "diagram.replaced": "Importación",
};

export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind;
}

// [with a name, without one]
const COMMAND_TEXT: Record<string, [string, string]> = {
  AddClass: ["Agregó la clase", "Agregó una clase"],
  RemoveClass: ["Eliminó la clase", "Eliminó una clase"],
  RenameClass: ["Renombró una clase a", "Renombró una clase"],
  AddAttribute: ["Agregó el atributo", "Agregó un atributo"],
  RemoveAttribute: ["Eliminó el atributo", "Eliminó un atributo"],
  AddOperation: ["Agregó la operación", "Agregó una operación"],
  RemoveOperation: ["Eliminó la operación", "Eliminó una operación"],
  AddRelationship: ["Agregó la relación", "Agregó una relación"],
  RemoveRelationship: ["Eliminó la relación", "Eliminó una relación"],
  UpdateRelationship: ["Editó la relación", "Editó una relación"],
  SetGenerationProfile: ["Cambió el perfil de generación de", "Cambió un perfil de generación"],
};

type DescribedCommand = { type: string; label: string | null };

function describeCommand({ type, label }: DescribedCommand): string {
  const text = COMMAND_TEXT[type];
  if (!text) return type;
  return label ? `${text[0]} «${label}»` : text[1];
}

const plural = (count: number, one: string, many: string) => `${count} ${count === 1 ? one : many}`;

/** One Spanish sentence for an entry, built from its kind and structured data. Never throws. */
export function describeEntry(entry: LogEntry): string {
  const data = entry.data ?? {};
  switch (entry.kind) {
    case "change": {
      const commands = Array.isArray(data.commands) ? (data.commands as DescribedCommand[]) : [];
      if (commands.length === 0) return "Cambió el diagrama";
      const total = typeof data.total === "number" ? data.total : commands.length;
      const parts = commands.map(describeCommand);
      if (total > commands.length) parts.push(`y ${plural(total - commands.length, "cambio", "cambios")} más`);
      return parts.join("; ");
    }
    case "version.restored":
      return typeof data.version_number === "number" ? `Restauró la versión ${data.version_number}` : "Restauró una versión";
    case "diagram.replaced":
      return "Reemplazó el contenido del diagrama con una importación";
    case "proposal.created": {
      const changes = Array.isArray(data.changes) ? data.changes.length : 0;
      const who = typeof data.requested_by === "string" && data.requested_by ? `, a petición de ${data.requested_by}` : "";
      return `Propuso ${plural(changes, "cambio", "cambios")}${who}`;
    }
    case "proposal.approved": {
      const applied = Array.isArray(data.applied_indices) ? data.applied_indices.length : 0;
      const total = typeof data.total_changes === "number" ? data.total_changes : applied;
      return `Aprobó la propuesta de la IA (${applied} de ${total} cambios)`;
    }
    case "proposal.rejected":
      return "Rechazó la propuesta de la IA";
    default:
      return entry.summary;
  }
}

/** The people (and the AI) that can be filtered on, each once, in order of appearance. */
export function userOptions(sessions: LogSession[]): { value: string; label: string }[] {
  const options = new Map<string, string>();
  for (const session of sessions) {
    for (const actor of session.actors) {
      const value = actor.is_ai ? "ai" : actor.id;
      if (value && !options.has(value)) options.set(value, actor.label);
    }
  }
  return [...options].map(([value, label]) => ({ value, label }));
}
