import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import { wsUrl } from "@/lib/env";
import {
  attributeTypeLabel,
  createDocument,
  formatMultiplicity,
  getDocument,
  listDocuments,
  openDocumentSocket,
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

  it("submitCommand forwards RemoveClass verbatim as the JSON body", async () => {
    const commandResult = { revision: 6, validation: { is_valid: true, violations: [] } };
    vi.mocked(api.apiFetch).mockResolvedValueOnce(commandResult);

    const command = { type: "RemoveClass" as const, class_id: "c1" };
    const result = await submitCommand("acme", documentFixture.id, command);

    expect(api.apiFetch).toHaveBeenCalledWith(
      `/api/orgs/acme/documents/${documentFixture.id}/commands`,
      expect.objectContaining({ method: "POST", json: command }),
    );
    expect(result).toEqual(commandResult);
  });

  it("submitCommand forwards RemoveAttribute verbatim as the JSON body", async () => {
    const commandResult = { revision: 7, validation: { is_valid: true, violations: [] } };
    vi.mocked(api.apiFetch).mockResolvedValueOnce(commandResult);

    const command = { type: "RemoveAttribute" as const, class_id: "c1", attribute_id: "a1" };
    const result = await submitCommand("acme", documentFixture.id, command);

    expect(api.apiFetch).toHaveBeenCalledWith(
      `/api/orgs/acme/documents/${documentFixture.id}/commands`,
      expect.objectContaining({ method: "POST", json: command }),
    );
    expect(result).toEqual(commandResult);
  });

  it("submitCommand forwards RemoveRelationship verbatim as the JSON body", async () => {
    const commandResult = { revision: 8, validation: { is_valid: true, violations: [] } };
    vi.mocked(api.apiFetch).mockResolvedValueOnce(commandResult);

    const command = { type: "RemoveRelationship" as const, relationship_id: "r1" };
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

  it("listDocuments gets /api/orgs/{slug}/documents with no method override", async () => {
    const summaries = [
      { id: "doc-1", name: "Ventas", revision: 4, updated_at: "2026-09-12T10:05:00Z" },
    ];
    vi.mocked(api.apiFetch).mockResolvedValueOnce(summaries);

    const result = await listDocuments("a b");

    expect(api.apiFetch).toHaveBeenCalledWith("/api/orgs/a%20b/documents");
    expect(result).toEqual(summaries);
  });

  it("listDocuments propagates a rejected apiFetch as ApiError verbatim", async () => {
    const error = new ApiError({ status: 404, code: "not_found", detail: "Organization not found" });
    vi.mocked(api.apiFetch).mockRejectedValueOnce(error);

    await expect(listDocuments("acme")).rejects.toBe(error);
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

  /**
   * `openDocumentSocket` is the sole place that builds a WS URL
   * (design.md DD11/DD13) — everything else in the app reaches it through
   * `useDocument`'s socket effect.
   */
  describe("openDocumentSocket", () => {
    class MockWebSocket {
      static instances: MockWebSocket[] = [];
      url: string;
      onopen: (() => void) | null = null;
      onmessage: ((event: { data: string }) => void) | null = null;
      onclose: ((event: unknown) => void) | null = null;
      onerror: ((event: unknown) => void) | null = null;
      closed = false;

      constructor(url: string | URL) {
        this.url = url.toString();
        MockWebSocket.instances.push(this);
      }

      close() {
        this.closed = true;
      }
    }

    beforeEach(() => {
      MockWebSocket.instances = [];
      vi.stubGlobal("WebSocket", MockWebSocket);
    });

    it("builds the WS URL from wsUrl and wires onopen/onmessage/onclose/onerror", () => {
      const onOpen = vi.fn();
      const onMessage = vi.fn();
      const onClose = vi.fn();
      const onError = vi.fn();

      openDocumentSocket("acme", documentFixture.id, { onOpen, onMessage, onClose, onError });

      const socket = MockWebSocket.instances[0]!;
      expect(socket.url).toBe(`${wsUrl}/ws/orgs/acme/documents/${documentFixture.id}/`);

      socket.onopen?.();
      expect(onOpen).toHaveBeenCalledOnce();

      socket.onmessage?.({
        data: JSON.stringify({ type: "document.update", document: documentFixture }),
      });
      expect(onMessage).toHaveBeenCalledWith(documentFixture);

      const closeEvent = { code: 4401 };
      socket.onclose?.(closeEvent);
      expect(onClose).toHaveBeenCalledWith(closeEvent);

      const errorEvent = {};
      socket.onerror?.(errorEvent);
      expect(onError).toHaveBeenCalledWith(errorEvent);
    });

    it("encodes orgSlug and docId into the path", () => {
      openDocumentSocket("a b", "doc/1", { onMessage: vi.fn(), onClose: vi.fn() });

      const socket = MockWebSocket.instances[0]!;
      expect(socket.url).toBe(`${wsUrl}/ws/orgs/a%20b/documents/doc%2F1/`);
    });

    it("ignores a message whose type is not document.update", () => {
      const onMessage = vi.fn();
      openDocumentSocket("acme", documentFixture.id, { onMessage, onClose: vi.fn() });

      const socket = MockWebSocket.instances[0]!;
      socket.onmessage?.({ data: JSON.stringify({ type: "something.else", document: {} }) });

      expect(onMessage).not.toHaveBeenCalled();
    });
  });
});
