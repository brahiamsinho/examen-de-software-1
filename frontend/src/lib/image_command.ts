import { apiFetch } from "@/lib/api";
import type { VoiceCommandResult } from "@/lib/voice_command";

/**
 * Domain client for `apps/ai_assistant`'s image-driven diagram import: one
 * endpoint that turns an uploaded UML diagram image into a sequence of
 * applied UML commands via OpenAI vision function calling. Mirrors
 * `lib/voice_command.ts`'s thin `apiFetch` wrapper style and reuses its
 * `VoiceCommandResult` shape — the response body is identical, only the
 * input modality (image instead of transcript) differs.
 */

// Much longer than `voice_command.ts`'s own timeout: an image upload + vision
// call has more to process than a short transcript, and a local CPU-only model
// (LLM_PROVIDER=local) needs minutes. Matches LOCAL_LLM_TIMEOUT_SECONDS's
// suggested ceiling so the browser never gives up before the backend does.
const IMAGE_COMMAND_TIMEOUT_MS = 600_000;

export function postImageCommand(
  orgSlug: string,
  docId: string,
  file: File,
): Promise<VoiceCommandResult> {
  const formData = new FormData();
  formData.append("file", file);
  // No `json` field: `apiFetch` then passes `body` through to `fetch`
  // as-is and never force-sets `Content-Type`, so the browser sets the
  // multipart boundary itself.
  return apiFetch<VoiceCommandResult>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/image-command`,
    { method: "POST", body: formData, signal: AbortSignal.timeout(IMAGE_COMMAND_TIMEOUT_MS) },
  );
}

export type ImageImportPreview = {
  plan_id: string;
  base_revision: number;
  changes: VoiceCommandResult["applied"];
};

export function previewImageImport(orgSlug: string, docId: string, file: File): Promise<ImageImportPreview> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch<ImageImportPreview>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/image-import-preview`,
    { method: "POST", body: formData, signal: AbortSignal.timeout(IMAGE_COMMAND_TIMEOUT_MS) },
  );
}

export function confirmImageImport(
  orgSlug: string,
  docId: string,
  planId: string,
): Promise<VoiceCommandResult> {
  return apiFetch<VoiceCommandResult>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/image-import-confirm`,
    { method: "POST", json: { plan_id: planId } },
  );
}
