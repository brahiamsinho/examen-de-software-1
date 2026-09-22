import { apiFetch } from "@/lib/api";

/**
 * Domain client for `apps/ai_assistant`'s voice-driven diagram editing:
 * one endpoint that turns a transcript into a sequence of applied UML
 * commands via Gemini function calling. Mirrors `lib/join_tables.ts`'s
 * thin `apiFetch` wrapper style.
 */
export type AppliedVoiceCommand = { ok: boolean; message: string };

export type VoiceCommandResult = {
  revision: number;
  applied: AppliedVoiceCommand[];
};

// Slightly longer than the backend's own Gemini request timeout
// (`REQUEST_TIMEOUT_MS` in `apps/ai_assistant/gemini_client.py`, 45s — real
// measurement against the live API showed 19-25s+ for a trivial prompt on
// one dev machine's network), so a timed-out Gemini call surfaces the
// backend's clean 502/504 first instead of the frontend aborting the
// connection out from under it.
const VOICE_COMMAND_TIMEOUT_MS = 50_000;

export function postVoiceCommand(
  orgSlug: string,
  docId: string,
  transcript: string,
): Promise<VoiceCommandResult> {
  return apiFetch<VoiceCommandResult>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/voice-command`,
    { method: "POST", json: { transcript }, signal: AbortSignal.timeout(VOICE_COMMAND_TIMEOUT_MS) },
  );
}
