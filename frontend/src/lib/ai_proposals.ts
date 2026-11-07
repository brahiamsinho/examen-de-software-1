import { apiFetch } from "@/lib/api";
import type { RelationshipKind, UmlModel } from "@/lib/uml_documents";

/**
 * Domain client for AI board proposals (`apps/ai_assistant`, issue #15): the
 * AI suggests changes as drafts that never touch the diagram until an
 * OWNER/EDITOR approves them. Every member sees pending proposals live over
 * the document socket (`proposal.update`).
 */
export type ProposalStatus = "pending" | "approved" | "rejected" | "stale";

export type AiProposalCall = { name: string; args: Record<string, unknown> };

export type AiProposal = {
  id: string;
  document_id: string;
  status: ProposalStatus;
  prompt: string;
  base_revision: number;
  changes: { ok: boolean; message: string }[];
  calls: AiProposalCall[];
  /** Which changes the approver chose to apply (null until decided). */
  applied_indices: number[] | null;
  requested_by: string | null;
  decided_by: string | null;
  created_at: string;
  decided_at: string | null;
};

const base = (orgSlug: string, docId: string) =>
  `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/ai-proposals`;

// The model can take a while to answer; mirrors the other AI calls' generous timeout.
const ASK_TIMEOUT_MS = 60_000;

export function listProposals(orgSlug: string, docId: string): Promise<AiProposal[]> {
  return apiFetch<AiProposal[]>(base(orgSlug, docId));
}

export function requestProposal(orgSlug: string, docId: string, prompt: string): Promise<AiProposal> {
  return apiFetch<AiProposal>(base(orgSlug, docId), {
    method: "POST",
    json: { prompt },
    signal: AbortSignal.timeout(ASK_TIMEOUT_MS),
  });
}

/** `selected` = indices of the changes to apply; omitted applies every change. */
export function approveProposal(
  orgSlug: string,
  docId: string,
  proposalId: string,
  selected?: number[],
): Promise<AiProposal> {
  return apiFetch<AiProposal>(`${base(orgSlug, docId)}/${encodeURIComponent(proposalId)}/approve`, {
    method: "POST",
    ...(selected === undefined ? {} : { json: { selected } }),
  });
}

export function rejectProposal(orgSlug: string, docId: string, proposalId: string): Promise<AiProposal> {
  return apiFetch<AiProposal>(`${base(orgSlug, docId)}/${encodeURIComponent(proposalId)}/reject`, { method: "POST" });
}

/** Keeps `proposals` equal to "what is still pending": a decided or stale one drops out. */
export function upsertProposal(proposals: AiProposal[], incoming: AiProposal): AiProposal[] {
  const others = proposals.filter((item) => item.id !== incoming.id);
  if (incoming.status !== "pending") return others;
  const existing = proposals.findIndex((item) => item.id === incoming.id);
  if (existing === -1) return [...others, incoming];
  const next = [...proposals];
  next[existing] = incoming;
  return next;
}

const normalizeName = (name: unknown) => String(name ?? "").trim().toLocaleLowerCase();

/**
 * For each change, the indices of the changes it cannot exist without: an
 * attribute or operation needs the class it is added to, and a relationship
 * needs both of its classes, when those classes are created in the same
 * proposal. A class (or any change on an already existing class) needs nothing.
 */
function changeDependencies(calls: AiProposalCall[]): number[][] {
  const classIndex = new Map<string, number>();
  calls.forEach((call, index) => {
    if (call.name === "add_class") classIndex.set(normalizeName(call.args.name), index);
  });
  return calls.map((call) => {
    const names =
      call.name === "add_attribute" || call.name === "add_operation"
        ? [call.args.class_name]
        : call.name === "add_relationship"
          ? [call.args.source_class_name, call.args.target_class_name]
          : [];
    return names.flatMap((name) => {
      const index = classIndex.get(normalizeName(name));
      return index === undefined ? [] : [index];
    });
  });
}

/** Every change that can be applied: the starting point of the approval checkboxes. */
export function defaultSelection(proposal: AiProposal): Set<number> {
  return new Set(proposal.changes.flatMap((change, index) => (change.ok ? [index] : [])));
}

/**
 * Flips one change and keeps the selection consistent, so it can always be
 * applied: selecting an attribute/relationship also selects the classes it
 * needs, and unselecting a class also unselects what depends on it.
 */
export function toggleChange(calls: AiProposalCall[], selected: ReadonlySet<number>, index: number): Set<number> {
  const dependencies = changeDependencies(calls);
  const next = new Set(selected);
  if (next.has(index)) {
    next.delete(index);
    let changed = true;
    while (changed) {
      changed = false;
      dependencies.forEach((needs, dependent) => {
        if (next.has(dependent) && needs.some((needed) => !next.has(needed))) {
          next.delete(dependent);
          changed = true;
        }
      });
    }
  } else {
    next.add(index);
    dependencies[index]?.forEach((needed) => next.add(needed));
  }
  return next;
}

export type AiDraftClass = {
  id: string;
  name: string;
  attributes: string[];
  operations: string[];
  proposalId: string;
};
export type AiDraftRelationship = {
  id: string;
  source: string;
  target: string;
  kind: RelationshipKind;
  name: string;
  /** Multiplicity at each end, as the AI gave it (or the backend's default). */
  sourceMultiplicity: string;
  targetMultiplicity: string;
  proposalId: string;
};
export type AiDrafts = { classes: AiDraftClass[]; relationships: AiDraftRelationship[] };

const normalize = normalizeName;

/**
 * Derives what the canvas draws for the pending proposals: new classes (with
 * the attributes the AI proposes for them) and the relationships between known
 * or draft classes. Pure and visual only: it never edits the model. Changes it
 * cannot draw (renames, removals, attributes of an existing class) stay in the
 * proposal panel's text list.
 */
export function buildAiDrafts(model: UmlModel, proposals: AiProposal[]): AiDrafts {
  const drafts: AiDrafts = { classes: [], relationships: [] };
  const existing = new Map(model.classes.map((item) => [normalize(item.name), item.id]));

  for (const proposal of proposals) {
    if (proposal.status !== "pending") continue;
    const known = new Map(existing);
    const draftByName = new Map<string, AiDraftClass>();

    proposal.calls.forEach((call, index) => {
      const args = call.args;
      if (call.name === "add_class") {
        const key = normalize(args.name);
        if (!key || known.has(key)) return;
        const draft: AiDraftClass = {
          id: `ai-draft:${proposal.id}:${key}`,
          name: String(args.name).trim(),
          attributes: [],
          operations: [],
          proposalId: proposal.id,
        };
        known.set(key, draft.id);
        draftByName.set(key, draft);
        drafts.classes.push(draft);
      } else if (call.name === "add_attribute") {
        const target = draftByName.get(normalize(args.class_name));
        if (target) target.attributes.push(`- ${String(args.attribute_name)}: ${String(args.attribute_type)}`);
      } else if (call.name === "add_operation") {
        const target = draftByName.get(normalize(args.class_name));
        if (target) target.operations.push(`+ ${String(args.operation_name)}()`);
      } else if (call.name === "add_relationship") {
        const source = known.get(normalize(args.source_class_name));
        const target = known.get(normalize(args.target_class_name));
        if (!source || !target) return;
        drafts.relationships.push({
          id: `ai-draft-edge:${proposal.id}:${index}`,
          source,
          target,
          kind: args.kind as RelationshipKind,
          name: String(args.name ?? ""),
          // Same defaults as the backend translator, so the draft shows what approving would create.
          sourceMultiplicity: String(args.source_multiplicity || "0..1"),
          targetMultiplicity: String(args.target_multiplicity || "0..*"),
          proposalId: proposal.id,
        });
      }
    });
  }
  return drafts;
}
