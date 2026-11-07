"use client";

import { AlertCircle, Sparkles } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { defaultSelection, toggleChange, type AiProposal } from "@/lib/ai_proposals";

type Props = {
  proposals: AiProposal[];
  /** OWNER/EDITOR: may ask the AI and approve or reject. The backend re-checks it. */
  canDecide: boolean;
  /** The proposal currently being approved/rejected, if any. */
  busyId: string | null;
  asking: boolean;
  error: string | null;
  onAsk: (prompt: string) => Promise<void>;
  /** `selected` = indices of the changes to apply, in order. */
  onApprove: (proposalId: string, selected: number[]) => void;
  onReject: (proposalId: string) => void;
};

type CardProps = {
  proposal: AiProposal;
  canDecide: boolean;
  busy: boolean;
  onApprove: Props["onApprove"];
  onReject: Props["onReject"];
};

/**
 * One pending proposal. An editor chooses which changes to apply with
 * checkboxes (one, some or all). The selection keeps itself applicable:
 * choosing an attribute also chooses its class, and unchoosing a class also
 * unchooses what hangs from it (`toggleChange`). A change that cannot be
 * applied stays unchecked and disabled. Own state per card, so each proposal
 * keeps its own selection.
 */
function ProposalCard({ proposal, canDecide, busy, onApprove, onReject }: CardProps) {
  const [selected, setSelected] = useState<Set<number>>(() => defaultSelection(proposal));
  const total = proposal.changes.length;
  const everything = selected.size === total;

  return (
    <li className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-3">
      <p className="text-xs text-muted-foreground">
        Pedida por {proposal.requested_by ?? "alguien"}: &ldquo;{proposal.prompt}&rdquo;
      </p>

      {canDecide ? (
        <>
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Elige qué aplicar</span>
            <span className="flex gap-1">
              <Button type="button" size="xs" variant="ghost" onClick={() => setSelected(defaultSelection(proposal))}>
                Todos
              </Button>
              <Button type="button" size="xs" variant="ghost" onClick={() => setSelected(new Set())}>
                Ninguno
              </Button>
            </span>
          </div>
          <ul className="flex flex-col gap-1 text-sm">
            {proposal.changes.map((change, index) => (
              <li key={index}>
                <label className={`flex items-start gap-2 ${change.ok ? "" : "text-destructive"}`}>
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.has(index)}
                    disabled={!change.ok || busy}
                    onChange={() => setSelected((current) => toggleChange(proposal.calls, current, index))}
                  />
                  <span>{change.message}</span>
                </label>
              </li>
            ))}
          </ul>
          <div className="flex justify-end gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => onReject(proposal.id)} disabled={busy}>
              Rechazar
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={() => onApprove(proposal.id, [...selected].sort((a, b) => a - b))}
              disabled={busy || selected.size === 0}
            >
              {everything ? `Aprobar todo (${selected.size})` : `Aprobar selección (${selected.size})`}
            </Button>
          </div>
        </>
      ) : (
        <ul className="flex flex-col gap-1 text-sm">
          {proposal.changes.map((change, index) => (
            <li key={index} className={change.ok ? undefined : "text-destructive"}>
              <span aria-hidden="true">{change.ok ? "•" : "⚠"}</span> <span>{change.message}</span>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

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
          {proposals.map((proposal) => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              canDecide={canDecide}
              busy={busyId === proposal.id}
              onApprove={onApprove}
              onReject={onReject}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
