import { describe, expect, it } from "vitest";

import {
  buildAiDrafts,
  defaultSelection,
  toggleChange,
  upsertProposal,
  type AiProposal,
} from "@/lib/ai_proposals";
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
    applied_indices: null,
    decided_by: null,
    created_at: "2026-11-07T10:00:00Z",
    decided_at: null,
    ...overrides,
  };
}

// 0 Pedido, 1 Cliente, 2 Pedido.total, 3 Cliente -> Pedido
const calls = [
  { name: "add_class", args: { name: "Pedido" } },
  { name: "add_class", args: { name: "Cliente" } },
  { name: "add_attribute", args: { class_name: "pedido", attribute_name: "total", attribute_type: "Decimal" } },
  { name: "add_relationship", args: { kind: "association", source_class_name: "Cliente", target_class_name: "Pedido" } },
];

describe("change selection", () => {
  it("selects every change that can be applied by default and skips the broken ones", () => {
    const withBroken = proposal({
      calls,
      changes: [{ ok: true, message: "a" }, { ok: false, message: "b" }, { ok: true, message: "c" }, { ok: true, message: "d" }],
    });

    expect([...defaultSelection(withBroken)]).toEqual([0, 2, 3]);
  });

  it("selecting an attribute also selects the class it belongs to", () => {
    expect([...toggleChange(calls, new Set(), 2)].sort()).toEqual([0, 2]);
  });

  it("selecting a relationship selects both of its classes", () => {
    expect([...toggleChange(calls, new Set(), 3)].sort()).toEqual([0, 1, 3]);
  });

  it("unselecting a class also unselects its attributes and relationships", () => {
    const all = new Set([0, 1, 2, 3]);

    expect([...toggleChange(calls, all, 0)].sort()).toEqual([1]);
    expect([...toggleChange(calls, all, 1)].sort()).toEqual([0, 2]);
  });

  it("unselecting only an attribute leaves its class selected", () => {
    expect([...toggleChange(calls, new Set([0, 2]), 2)]).toEqual([0]);
  });

  it("does not mutate the selection it receives", () => {
    const original = new Set([0]);

    toggleChange(calls, original, 1);

    expect([...original]).toEqual([0]);
  });
});

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
      { id: "ai-draft:p1:pedido", name: "Pedido", attributes: ["- total: FLOAT"], operations: [], proposalId: "p1" },
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
      {
        id: "ai-draft-edge:p1:1",
        source: "c-persona",
        target: "ai-draft:p1:pedido",
        kind: "association",
        name: "",
        // The same defaults the backend applies when the AI gives none.
        sourceMultiplicity: "0..1",
        targetMultiplicity: "0..*",
        proposalId: "p1",
      },
    ]);
  });

  it("carries the multiplicity of each end and the name, so a many-to-many draft reads as one", () => {
    const drafts = buildAiDrafts(model, [
      proposal({
        calls: [
          { name: "add_class", args: { name: "Rol" } },
          {
            name: "add_relationship",
            args: {
              kind: "association",
              source_class_name: "Persona",
              target_class_name: "Rol",
              source_multiplicity: "0..*",
              target_multiplicity: "1..*",
              name: "tiene",
            },
          },
        ],
      }),
    ]);

    expect(drafts.relationships[0]).toMatchObject({
      name: "tiene",
      sourceMultiplicity: "0..*",
      targetMultiplicity: "1..*",
    });
  });

  it("shows the operations the AI proposes on a draft class", () => {
    const drafts = buildAiDrafts(model, [
      proposal({
        calls: [
          { name: "add_class", args: { name: "Pedido" } },
          { name: "add_operation", args: { class_name: "Pedido", operation_name: "calcular" } },
        ],
      }),
    ]);

    expect(drafts.classes[0]!.operations).toEqual(["+ calcular()"]);
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
