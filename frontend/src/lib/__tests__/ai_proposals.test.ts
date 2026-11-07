import { describe, expect, it } from "vitest";

import { buildAiDrafts, upsertProposal, type AiProposal } from "@/lib/ai_proposals";
import type { UmlModel } from "@/lib/uml_documents";

function proposal(overrides: Partial<AiProposal> = {}): AiProposal {
  return {
    id: "p1",
    document_id: "d1",
    status: "pending",
    prompt: "ideas",
    base_revision: 1,
    changes: [],
    calls: [],
    requested_by: "Ana",
    decided_by: null,
    created_at: "2026-11-07T10:00:00Z",
    decided_at: null,
    ...overrides,
  };
}

const model: UmlModel = {
  classes: [{ id: "c-persona", name: "Persona", visibility: "public", attributes: [], operations: [] }],
  enumerations: [],
  relationships: [],
  generation_metadata: {},
};

describe("upsertProposal", () => {
  it("adds a pending proposal and replaces one with the same id", () => {
    const first = upsertProposal([], proposal());
    const second = upsertProposal(first, proposal({ prompt: "changed" }));

    expect(first).toHaveLength(1);
    expect(second).toHaveLength(1);
    expect(second[0].prompt).toBe("changed");
  });

  it("removes a proposal once it is approved, rejected or stale", () => {
    for (const status of ["approved", "rejected", "stale"] as const) {
      expect(upsertProposal([proposal()], proposal({ status }))).toEqual([]);
    }
  });

  it("ignores a decided proposal it never had", () => {
    expect(upsertProposal([], proposal({ status: "rejected" }))).toEqual([]);
  });
});

describe("buildAiDrafts", () => {
  it("draws a new class with the attributes the AI proposes for it", () => {
    const drafts = buildAiDrafts(model, [
      proposal({
        calls: [
          { name: "add_class", args: { name: "Pedido" } },
          { name: "add_attribute", args: { class_name: "pedido", attribute_name: "total", attribute_type: "FLOAT" } },
        ],
      }),
    ]);

    expect(drafts.classes).toEqual([
      { id: "ai-draft:p1:pedido", name: "Pedido", attributes: ["- total: FLOAT"], proposalId: "p1" },
    ]);
  });

  it("connects a draft class to an existing one, resolving names case-insensitively", () => {
    const drafts = buildAiDrafts(model, [
      proposal({
        calls: [
          { name: "add_class", args: { name: "Pedido" } },
          {
            name: "add_relationship",
            args: { kind: "association", source_class_name: "  PERSONA ", target_class_name: "Pedido" },
          },
        ],
      }),
    ]);

    expect(drafts.relationships).toEqual([
      { id: "ai-draft-edge:p1:1", source: "c-persona", target: "ai-draft:p1:pedido", kind: "association", proposalId: "p1" },
    ]);
  });

  it("never duplicates a class that already exists and skips relationships with an unknown end", () => {
    const drafts = buildAiDrafts(model, [
      proposal({
        calls: [
          { name: "add_class", args: { name: "persona" } },
          { name: "add_relationship", args: { kind: "association", source_class_name: "Persona", target_class_name: "Ghost" } },
          { name: "rename_class", args: { class_name: "Persona", new_name: "X" } },
        ],
      }),
    ]);

    expect(drafts.classes).toEqual([]);
    expect(drafts.relationships).toEqual([]);
  });

  it("ignores proposals that are no longer pending", () => {
    const drafts = buildAiDrafts(model, [
      proposal({ status: "stale", calls: [{ name: "add_class", args: { name: "Pedido" } }] }),
    ]);

    expect(drafts).toEqual({ classes: [], relationships: [] });
  });

  it("keeps draft ids unique across proposals that suggest the same class", () => {
    const calls = [{ name: "add_class", args: { name: "Pedido" } }];
    const drafts = buildAiDrafts(model, [proposal({ id: "a", calls }), proposal({ id: "b", calls })]);

    expect(drafts.classes.map((item) => item.id)).toEqual(["ai-draft:a:pedido", "ai-draft:b:pedido"]);
  });
});
