import { apiFetchBlob } from "@/lib/api";

/**
 * Domain client for `apps/generation_export` (one module per backend app).
 * Downloads the generated Spring Boot backend of a stored document through
 * the credentialed `apiFetchBlob` seam, then hands the zip to the browser
 * via a temporary object URL + anchor click.
 */

const FALLBACK_FILENAME = "modelia-backend.zip";

export async function downloadGeneratedBackend(orgSlug: string, docId: string): Promise<void> {
  const { blob, filename } = await apiFetchBlob(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/generate`,
  );

  const objectUrl = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename ?? FALLBACK_FILENAME;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
