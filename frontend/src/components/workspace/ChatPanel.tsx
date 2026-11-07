"use client";

import { AlertCircle, Send } from "lucide-react";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { mentionsAi, type ChatMessage } from "@/lib/ai_chat";

type Props = {
  messages: ChatMessage[];
  /** OWNER/EDITOR: may write. VIEWERs read only; the backend re-checks it. */
  canWrite: boolean;
  error: string | null;
  /** Rejects when the message could not be sent, so the text can be restored. */
  onSend: (content: string) => Promise<void>;
};

/**
 * Presentational group chat for one diagram. Everyone on the diagram sees every
 * message live, each with its author; the AI is one more participant and only
 * answers a message that mentions `@IA`. The container owns the API calls.
 * The field clears as soon as the message is sent, so people can keep typing
 * while the AI is still answering someone else's mention.
 */
export function ChatPanel({ messages, canWrite, error, onSend }: Props) {
  const [text, setText] = useState("");
  const [pendingMentions, setPendingMentions] = useState(0);
  const listRef = useRef<HTMLUListElement>(null);

  // Keeps the newest message in view without scrolling the whole page.
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [messages.length]);

  async function send() {
    const content = text.trim();
    if (!content) return;
    const wakesAi = mentionsAi(content);
    setText("");
    if (wakesAi) setPendingMentions((count) => count + 1);
    try {
      await onSend(content);
    } catch {
      // The container surfaces the error; give the text back unless they already typed something else.
      setText((current) => (current === "" ? content : current));
    } finally {
      if (wakesAi) setPendingMentions((count) => count - 1);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void send();
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {messages.length === 0 ? (
        <p className="text-sm text-muted-foreground">Todavía no hay mensajes. Escribe el primero.</p>
      ) : (
        <ul ref={listRef} className="flex max-h-72 flex-col gap-2 overflow-y-auto pr-1" aria-label="Mensajes del chat">
          {messages.map((message) => (
            <li
              key={message.id}
              className={`rounded-lg border px-3 py-2 text-sm ${
                message.is_ai ? "border-violet-500/30 bg-violet-500/10" : "border-border bg-muted/40"
              }`}
            >
              <span className={`text-xs font-semibold ${message.is_ai ? "text-violet-600" : "text-foreground"}`}>
                {message.author}
              </span>
              <p className="whitespace-pre-wrap break-words">{message.content}</p>
            </li>
          ))}
        </ul>
      )}

      {pendingMentions > 0 ? <p className="text-xs text-violet-600">La IA está pensando...</p> : null}

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {canWrite ? (
        <div className="flex flex-col gap-2">
          <label htmlFor="chat-message" className="sr-only">
            Mensaje para el equipo
          </label>
          <textarea
            id="chat-message"
            className="min-h-16 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            placeholder="Escribe al equipo..."
            maxLength={2000}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
          />
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs text-muted-foreground">Menciona @IA para que responda.</span>
            <Button type="button" size="sm" onClick={() => void send()} disabled={text.trim() === ""}>
              <Send />
              Enviar
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">Solo un editor puede escribir en el chat.</p>
      )}
    </div>
  );
}
