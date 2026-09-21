import { apiFetchBlob } from "@/lib/api";
import { saveBlobAsFile } from "@/lib/save_blob";

/**
 * Domain client for `apps/generation_export` (one module per backend app).
 * Downloads the generated Spring Boot backend of a stored document through
 * the credentialed `apiFetchBlob` seam, then hands the zip to the browser.
 */

const FALLBACK_FILENAME = "modelia-backend.zip";

export async function downloadGeneratedBackend(orgSlug: string, docId: string): Promise<void> {
  const { blob, filename } = await apiFetchBlob(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/generate`,
  );
  saveBlobAsFile(blob, filename ?? FALLBACK_FILENAME);
}
