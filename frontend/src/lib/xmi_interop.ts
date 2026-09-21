import { apiFetch, apiFetchBlob } from "@/lib/api";
import { saveBlobAsFile } from "@/lib/save_blob";
import type { UmlDocument } from "@/lib/uml_documents";

/**
 * Domain client for `apps/xmi_interop`: Enterprise Architect XMI import
 * (multipart upload -> new document + warnings) and export (XML download).
 */

const FALLBACK_FILENAME = "modelia-diagrama.xml";
const WARNINGS_KEY_PREFIX = "modelia.xmi-import-warnings.";

export type XmiImportResult = UmlDocument & { warnings: string[] };

function base(orgSlug: string): string {
  return `/api/orgs/${encodeURIComponent(orgSlug)}/documents`;
}

export async function importXmi(orgSlug: string, file: File): Promise<XmiImportResult> {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<XmiImportResult>(`${base(orgSlug)}/import-xmi`, { method: "POST", body });
}

export async function exportXmi(orgSlug: string, docId: string): Promise<void> {
  const { blob, filename } = await apiFetchBlob(
    `${base(orgSlug)}/${encodeURIComponent(docId)}/export-xmi`,
  );
  saveBlobAsFile(blob, filename ?? FALLBACK_FILENAME);
}

/**
 * The import response is only seen by the dashboard, but the warnings must be
 * shown on the document page it navigates to: park them in sessionStorage for
 * exactly one read. Storage may be unavailable (private mode) — then they are
 * simply not shown.
 */
export function stashImportWarnings(docId: string, warnings: string[]): void {
  if (warnings.length === 0) return;
  try {
    sessionStorage.setItem(WARNINGS_KEY_PREFIX + docId, JSON.stringify(warnings));
  } catch {
    /* storage unavailable: warnings are best-effort */
  }
}

export function takeImportWarnings(docId: string): string[] {
  try {
    const raw = sessionStorage.getItem(WARNINGS_KEY_PREFIX + docId);
    sessionStorage.removeItem(WARNINGS_KEY_PREFIX + docId);
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((w): w is string => typeof w === "string") : [];
  } catch {
    return [];
  }
}

/**
 * Loads an XMI file INTO an existing blank document (replacing its model).
 * The server answers 409 `document_not_empty` when the document already has
 * classes or relationships.
 */
export async function importXmiIntoDocument(
  orgSlug: string,
  docId: string,
  file: File,
): Promise<XmiImportResult> {
  const body = new FormData();
  body.append("file", file);
  return apiFetch<XmiImportResult>(`${base(orgSlug)}/${encodeURIComponent(docId)}/import-xmi`, {
    method: "POST",
    body,
  });
}
