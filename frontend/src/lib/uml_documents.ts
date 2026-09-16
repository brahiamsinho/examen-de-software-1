import { apiFetch } from "@/lib/api";
import { wsUrl } from "@/lib/env";

/**
 * Domain client for `apps/uml_documents` (design.md's `lib/uml_documents.ts`
 * — one module per backend Django app, mirroring `lib/organizations.ts`).
 * Types are hand-written and pinned to a real `codec._encode_model` /
 * `_document_out(...)` output (design.md DD1) because `model`/`layout` are
 * `dict` on the wire with no schema codegen; the pinned fixture lives in
 * this module's test suite and `DiagramCanvas.test.tsx`'s `toElements`
 * suite, so drift fails a test rather than a runtime render.
 */

export type PrimitiveType =
  | "String"
  | "Text"
  | "Integer"
  | "Long"
  | "Decimal"
  | "Boolean"
  | "Date"
  | "DateTime";

export const PRIMITIVE_TYPES: readonly PrimitiveType[] = [
  "String",
  "Text",
  "Integer",
  "Long",
  "Decimal",
  "Boolean",
  "Date",
  "DateTime",
];

export type EnumerationRef = { enumeration_ref: { enumeration_id: string } };
export type AttributeType = PrimitiveType | EnumerationRef;
export type Visibility = "public" | "private" | "protected" | "package";

export type UmlAttribute = {
  id: string;
  name: string;
  type: AttributeType;
  visibility: Visibility;
};

export type UmlOperation = {
  id: string;
  name: string;
  return_type: AttributeType | null;
  parameters: { name: string; type: AttributeType }[];
  visibility: Visibility;
};

export type UmlClass = {
  id: string;
  name: string;
  visibility: Visibility;
  attributes: UmlAttribute[];
  operations: UmlOperation[];
};

export type Multiplicity = { lower: number; upper: number | null };

export type RelationshipEnd = {
  class_id: string;
  multiplicity: Multiplicity;
  role: string | null;
};

export type RelationshipKind = "association" | "aggregation" | "composition" | "generalization";

export type Relationship = {
  id: string;
  kind: RelationshipKind;
  source: RelationshipEnd;
  target: RelationshipEnd;
  name: string | null;
};

export type UmlModel = {
  classes: UmlClass[];
  enumerations: {
    id: string;
    name: string;
    literals: { id: string; name: string; value: string }[];
  }[];
  relationships: Relationship[];
  generation_metadata: Record<string, unknown>;
};

export type DiagramLayout = { positions: Record<string, { x: number; y: number }> };

export type UmlDocument = {
  id: string;
  owner_id: string;
  revision: number;
  metadata: { name: string; description: string };
  model: UmlModel;
  layout: DiagramLayout;
  created_at: string;
  updated_at: string;
};

export type Diagnostic = { severity: "error" | "warning"; code: string; message: string; path: string };

export type CommandResult = {
  revision: number;
  validation: { is_valid: boolean; violations: Diagnostic[] };
};

/**
 * Six of the seven backend command shapes. Only `RenameClass` remains
 * unwired — no UI collects a new name (proposal §Out of Scope).
 * Field names are copied from `apps/uml_documents/schemas.py`.
 */
export type UmlCommandIn =
  | { type: "AddClass"; class_id: string; name: string }
  | {
      type: "AddAttribute";
      class_id: string;
      attribute: { id: string; name: string; type: AttributeType; visibility?: Visibility };
    }
  | {
      type: "AddRelationship";
      relationship: {
        id: string;
        kind: RelationshipKind;
        name?: string | null;
        // DD12: multiplicity goes OUT as a UML string, comes BACK as {lower, upper}.
        source: { class_id: string; multiplicity: string; role?: string | null };
        target: { class_id: string; multiplicity: string; role?: string | null };
      };
    }
  | { type: "RemoveClass"; class_id: string }
  | { type: "RemoveAttribute"; class_id: string; attribute_id: string }
  | { type: "RemoveRelationship"; relationship_id: string };

const base = (orgSlug: string) => `/api/orgs/${encodeURIComponent(orgSlug)}/documents`;

/**
 * Thin `apiFetch` wrappers (design.md DD1, mirroring `lib/organizations.ts`):
 * no `try/catch` here so `ApiError` — including the 403 from `require_role`
 * and the 422 `invalid_command_payload` — reaches the caller verbatim.
 */
export async function createDocument(
  orgSlug: string,
  input: { name: string },
): Promise<UmlDocument> {
  return apiFetch<UmlDocument>(base(orgSlug), { method: "POST", json: input });
}

export async function getDocument(orgSlug: string, docId: string): Promise<UmlDocument> {
  return apiFetch<UmlDocument>(`${base(orgSlug)}/${encodeURIComponent(docId)}`);
}

/**
 * Lightweight list-row shape (design.md DD2/DD4) — `name` is FLAT, unlike
 * `UmlDocument.metadata.name`. The two are NOT interchangeable.
 */
export type DocumentSummary = {
  id: string;
  name: string;
  revision: number;
  updated_at: string;
};

export async function listDocuments(orgSlug: string): Promise<DocumentSummary[]> {
  return apiFetch<DocumentSummary[]>(base(orgSlug));
}

export async function submitCommand(
  orgSlug: string,
  docId: string,
  command: UmlCommandIn,
): Promise<CommandResult> {
  return apiFetch<CommandResult>(`${base(orgSlug)}/${encodeURIComponent(docId)}/commands`, {
    method: "POST",
    json: command,
  });
}

/** Mirrors backend `format_multiplicity` for the edge label (DD12). */
export function formatMultiplicity(m: Multiplicity): string {
  if (m.upper === null) {
    return `${m.lower}..*`;
  }
  if (m.lower === m.upper) {
    return `${m.lower}`;
  }
  return `${m.lower}..${m.upper}`;
}

/** A primitive string renders as itself; an `EnumerationRef` renders its enum id. */
export function attributeTypeLabel(t: AttributeType): string {
  return typeof t === "string" ? t : t.enumeration_ref.enumeration_id;
}

/**
 * Node lock/position message shapes (design.md Message Contract, DD9):
 * server->client group events re-derive `mine` per connection and never
 * carry `owner_token` — these types mirror that wire shape exactly, one
 * field set per inbound `type`.
 */
export type NodeLockedIn = { type: "node.locked"; class_id: string; owner_label: string; mine: boolean };
export type NodeUnlockedIn = { type: "node.unlocked"; class_id: string };
export type NodePositionIn = {
  type: "node.position";
  class_id: string;
  x: number;
  y: number;
  mine: boolean;
};
export type NodeLockEntry = { class_id: string; owner_label: string; mine: boolean };
export type NodeLocksIn = { type: "node.locks"; locks: NodeLockEntry[] };
export type NodeClaimRejectedIn = { type: "node.claim_rejected"; class_id: string; owner_label: string };

export type DocumentSocketHandlers = {
  onOpen?: () => void;
  onMessage: (document: UmlDocument) => void;
  onClose: (event: { code: number }) => void;
  onError?: (event: unknown) => void;
  onNodeLocked?: (payload: NodeLockedIn) => void;
  onNodeUnlocked?: (payload: NodeUnlockedIn) => void;
  onNodePosition?: (payload: NodePositionIn) => void;
  onNodeLocks?: (payload: NodeLocksIn) => void;
  onClaimRejected?: (payload: NodeClaimRejectedIn) => void;
};

/**
 * `openDocumentSocket`'s return value (design.md's DiagramCanvas
 * Interfaces/Contracts block): `close()` plus one send helper per inbound
 * client->server message kind, so `state/document.ts` never touches the
 * raw `WebSocket` or reconstructs a frame shape itself.
 */
export type DocumentSocketConnection = {
  close: () => void;
  sendClaim: (classId: string) => void;
  sendPosition: (classId: string, x: number, y: number) => void;
  sendRelease: (classId: string, x: number | null, y: number | null) => void;
};

/**
 * The sole place that builds a WS URL (design.md DD9/DD11/DD13), mirroring
 * the HTTP route `/api/orgs/{slug}/documents/{docId}` at
 * `ws/orgs/{slug}/documents/{docId}/`. A thin transport seam: reconnect,
 * backoff, and the monotonic-revision merge all live in `useDocument`
 * (`state/document.ts`), not here.
 */
export function openDocumentSocket(
  orgSlug: string,
  docId: string,
  handlers: DocumentSocketHandlers,
): DocumentSocketConnection {
  const path = `/ws/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/`;
  const socket = new WebSocket(new URL(path, wsUrl));

  socket.onopen = () => handlers.onOpen?.();

  socket.onmessage = (event: { data: unknown }) => {
    const payload = JSON.parse(event.data as string) as { type: string } & Record<string, unknown>;
    switch (payload.type) {
      case "document.update":
        handlers.onMessage((payload as unknown as { document: UmlDocument }).document);
        break;
      case "node.locked":
        handlers.onNodeLocked?.(payload as unknown as NodeLockedIn);
        break;
      case "node.unlocked":
        handlers.onNodeUnlocked?.(payload as unknown as NodeUnlockedIn);
        break;
      case "node.position":
        handlers.onNodePosition?.(payload as unknown as NodePositionIn);
        break;
      case "node.locks":
        handlers.onNodeLocks?.(payload as unknown as NodeLocksIn);
        break;
      case "node.claim_rejected":
        handlers.onClaimRejected?.(payload as unknown as NodeClaimRejectedIn);
        break;
      default:
        break;
    }
  };

  socket.onclose = (event: { code: number }) => handlers.onClose(event);
  socket.onerror = (event: unknown) => handlers.onError?.(event);

  // A frame sent while the socket isn't OPEN would throw synchronously
  // (native `WebSocket.send`'s `InvalidStateError`) — every helper guards
  // on `readyState` instead of letting a stray drag-end frame during
  // reconnect crash the caller.
  const send = (payload: object) => {
    if (socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(payload));
    }
  };

  return {
    close: () => socket.close(),
    sendClaim: (classId) => send({ type: "node.claim", class_id: classId }),
    sendPosition: (classId, x, y) => send({ type: "node.position", class_id: classId, x, y }),
    sendRelease: (classId, x, y) => send({ type: "node.release", class_id: classId, x, y }),
  };
}
