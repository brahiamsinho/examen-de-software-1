import type { AiProposal } from "@/lib/ai_proposals";
import { apiFetch } from "@/lib/api";

/**
 * Domain client for the diagram's group chat (`apps/ai_assistant`, issue #16):
 * developers talk to each other and one AI model, which only answers when a
 * message mentions `@IA`. Every member sees messages live over the document
 * socket (`chat.message`); VIEWERs read but cannot write.
 */
export type ChatMessage = {
  /**
   * Database-assigned MongoDB ObjectId, as 24 lowercase hex characters. They are
   * fixed-width and start with the creation time, so comparing them as text
   * gives the one ordering of the chat (the same one the backend sorts by).
   */
  id: string;
  document_id: string;
  author: string;
  author_id: string | null;
  is_ai: boolean;
  content: string;
  created_at: string;
};

export type ChatPostResult = {
  message: ChatMessage;
  reply: ChatMessage | null;
  /** Set when the message was kept but the AI could not answer it. */
  ai_error: string | null;
  /** The draft the AI left on the board when the message asked it to change something. */
  proposal: AiProposal | null;
};

const base = (orgSlug: string, docId: string) =>
  `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/chat`;

// A mention waits for the model to answer. A local CPU-only model can take
// minutes, so this stays above the backend's LOCAL_LLM_TIMEOUT_SECONDS.
const POST_TIMEOUT_MS = 600_000;

/** Most messages kept in memory; the server only ever sends the latest ones anyway. */
export const MAX_CHAT_MESSAGES = 200;

export function listChat(orgSlug: string, docId: string): Promise<ChatMessage[]> {
  return apiFetch<ChatMessage[]>(base(orgSlug, docId));
}

export function postChat(orgSlug: string, docId: string, content: string): Promise<ChatPostResult> {
  return apiFetch<ChatPostResult>(base(orgSlug, docId), {
    method: "POST",
    json: { content },
    signal: AbortSignal.timeout(POST_TIMEOUT_MS),
  });
}

/**
 * Folds one message into the list: idempotent (a message arrives both from the
 * HTTP answer and from the socket), kept ordered by id (two people writing at
 * once can reach each client in a different order), and bounded.
 */
export function upsertChatMessage(messages: ChatMessage[], incoming: ChatMessage): ChatMessage[] {
  const others = messages.filter((item) => item.id !== incoming.id);
  const next = [...others, incoming].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return next.length > MAX_CHAT_MESSAGES ? next.slice(next.length - MAX_CHAT_MESSAGES) : next;
}

/**
 * Same rule as the backend (`chat._MENTION`): `@IA` as its own word, not inside an
 * email or `@IAmigos`. Python's `\w` is Unicode and JS's is ASCII-only without the
 * `u` flag, so the word characters are spelled out (letters, digits, underscore).
 */
const MENTION = /(?<![\p{L}\p{N}_@])@ia(?![\p{L}\p{N}_])/iu;

export function mentionsAi(content: string): boolean {
  return MENTION.test(content);
}
