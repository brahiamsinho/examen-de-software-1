import type { DocumentSummary } from "@/lib/uml_documents";

/**
 * Display helpers shared by the sidebar diagram list and the dashboard grid,
 * so an unnamed diagram reads the same everywhere ("Sin título") and dates
 * are formatted by one rule. The API allows an empty `name`.
 */
export const UNTITLED_DIAGRAM = "Sin título";

export function documentTitle(doc: Pick<DocumentSummary, "name">): string {
  return doc.name.trim() || UNTITLED_DIAGRAM;
}

const DATE_TIME = new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" });

/** Returns `null` for a missing/invalid timestamp so callers can omit the line. */
export function formatUpdatedAt(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : DATE_TIME.format(date);
}
