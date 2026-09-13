import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import {
  attributeTypeLabel,
  createDocument,
  formatMultiplicity,
  getDocument,
  submitCommand,
} from "@/lib/uml_documents";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiFetch: vi.fn(),
  };
});

/**
 * Pinned wire fixture verbatim from design.md's Interfaces/Contracts block
 * (`_document_out(...)` output) — the same fixture reused by
 * `DiagramCanvas.test.tsx`'s `toElements` suite so type drift fails a test
 * (DD1, proposal Risk 2).
 */
const documentFixture = {
  id: "6f1c2e2a-0000-4000-8000-000000000001",
  owner_id: "1",
  revision: 4,
  metadata: { name: "Ventas", description: "" },
  model: {
    classes: [
      {
        id: "c1",
        name: "Cliente",
        visibility: "public",
        attributes: [{ id: "a1", name: "nombre", type: "String", visibility: "private" }],
        operations: [],
      },
    ],
    enumerations: [],
    relationships: [
      {
        id: "r1",
        kind: "association",
        source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
        target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
        name: null,
      },
    ],
    generation_metadata: {},
  },
  layout: { positions: {} },
  created_at: "2026-09-12T10:00:00Z",
  updated_at: "2026-09-12T10:05:00Z",
};

describe("lib/uml_documents", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockReset();
  });

  it("createDocument posts to /api/orgs/{slug}/documents and returns the created document", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(documentFixture);

    const result = await createDocument("acme", { name: "Ventas" });

    expect(api.apiFetch).toHaveBeenCalledWith(
      "/api/orgs/acme/documents",
      expect.objectContaining({ method: "POST", json: { name: "Ventas" } }),
    );
    expect(result).toEqual(documentFixture);
  });

  it("getDocument gets /api/orgs/{slug}/documents/{docId} and returns the document", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(documentFixture);

    const result = await getDocument("acme", documentFixture.id);

    expect(api.apiFetch).toHaveBeenCalledWith(`/api/orgs/acme/documents/${documentFixture.id}`);
    expect(result).toEqual(documentFixture);
  });

  it("submitCommand posts the command to /api/orgs/{slug}/documents/{docId}/commands", async () => {
    const commandResult = { revision: 5, validation: { is_valid: true, violations: [] } };
    vi.mocked(api.apiFetch).mockResolvedValueOnce(commandResult);

    const command = { type: "AddClass" as const, class_id: "c2", name: "Producto" };
    const result = await submitCommand("acme", documentFixture.id, command);

    expect(api.apiFetch).toHaveBeenCalledWith(
      `/api/orgs/acme/documents/${documentFixture.id}/commands`,
      expect.objectContaining({ method: "POST", json: command }),
    );
    expect(result).toEqual(commandResult);
  });

  it("ApiError propagates unmodified from any of the three wrappers", async () => {
    const error = new ApiError({ status: 422, code: "invalid_command_payload", detail: "bad" });
    vi.mocked(api.apiFetch).mockRejectedValueOnce(error);

    await expect(getDocument("acme", documentFixture.id)).rejects.toBe(error);
  });

  describe("formatMultiplicity", () => {
    it('formats {lower: 1, upper: 1} as "1"', () => {
      expect(formatMultiplicity({ lower: 1, upper: 1 })).toBe("1");
    });

    it('formats {lower: 0, upper: 1} as "0..1"', () => {
      expect(formatMultiplicity({ lower: 0, upper: 1 })).toBe("0..1");
    });

    it('formats {lower: 0, upper: null} as "0..*"', () => {
      expect(formatMultiplicity({ lower: 0, upper: null })).toBe("0..*");
    });
  });

  describe("attributeTypeLabel", () => {
    it("returns a PrimitiveType string as itself", () => {
      expect(attributeTypeLabel("String")).toBe("String");
    });

    it("returns the enumeration id for an EnumerationRef", () => {
      expect(attributeTypeLabel({ enumeration_ref: { enumeration_id: "e1" } })).toBe("e1");
    });
  });
});
