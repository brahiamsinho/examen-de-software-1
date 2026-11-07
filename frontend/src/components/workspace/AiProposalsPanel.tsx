"use client";

import { AlertCircle, Sparkles } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { AiProposal } from "@/lib/ai_proposals";

type Props = {
  proposals: AiProposal[];
  /** OWNER/EDITOR: may ask the AI and approve or reject. The backend re-checks it. */
  canDecide: boolean;
  /** The proposal currently being approved/rejected, if any. */
  busyId: string | null;
  asking: boolean;
  error: string | null;
  onAsk: (prompt: string) => Promise<void>;
  onApprove: (proposalId: string) => void;
  onReject: (proposalId: string) => void;
};

/**
 * Presentational: lists the AI's pending drafts for everyone on the diagram and
 * lets an editor decide. The container owns the API calls, so this component
 * never imports the transport. Nothing here changes the diagram: a proposal is
 * a draft (also drawn dashed on the canvas) until someone approves it.
 */
export function AiProposalsPanel({ proposals, canDecide, busyId, asking, error, onAsk, onApprove, onReject }: Props) {
  const [prompt, setPrompt] = useState("");

  async function ask() {
    const text = prompt.trim();
    if (!text) return;
    try {
      await onAsk(text);
      setPrompt("");
    } catch {
      // The container surfaces the error; keep the text so the user can retry.
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {canDecide ? (
        <div className="flex flex-col gap-2">
          <label htmlFor="ai-proposal-prompt" className="text-sm font-medium">
            Pide ideas a la IA
          </label>
          <textarea
            id="ai-proposal-prompt"
            className="min-h-16 w-full rounded-lg border border-input bg-transparent px-3 py-2 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            placeholder="Ej.: ¿Qué clases o relaciones le faltan a este diagrama?"
            maxLength={2000}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            disabled={asking}
          />
          <Button type="button" size="sm" onClick={() => void ask()} disabled={asking || prompt.trim() === ""}>
            <Sparkles />
            {asking ? "Pensando..." : "Pedir ideas"}
          </Button>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          Solo un editor puede aprobar o rechazar las propuestas de la IA.
        </p>
      )}

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {proposals.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No hay propuestas pendientes. Lo que proponga la IA aparecerá aquí y en el diagrama como borrador.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {proposals.map((proposal) => {
            const blocked = proposal.changes.some((change) => !change.ok);
            const busy = busyId === proposal.id;
            return (
              <li key={proposal.id} className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-3">
                <p className="text-xs text-muted-foreground">
                  Pedida por {proposal.requested_by ?? "alguien"}: &ldquo;{proposal.prompt}&rdquo;
                </p>
                <ul className="flex flex-col gap-1 text-sm">
                  {proposal.changes.map((change, index) => (
                    <li key={index} className={change.ok ? undefined : "text-destructive"}>
                      <span aria-hidden="true">{change.ok ? "•" : "⚠"}</span> <span>{change.message}</span>
                    </li>
                  ))}
                </ul>
                {canDecide ? (
                  <div className="flex justify-end gap-2">
                    <Button type="button" size="sm" variant="outline" onClick={() => onReject(proposal.id)} disabled={busy}>
                      Rechazar
                    </Button>
                    <Button type="button" size="sm" onClick={() => onApprove(proposal.id)} disabled={busy || blocked}>
                      Aprobar
                    </Button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
