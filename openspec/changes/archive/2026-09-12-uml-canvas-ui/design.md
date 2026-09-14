# Design: UML Class-Diagram Canvas UI

## Technical Approach

Six new frontend modules plus one line in `dashboard/page.tsx`, layered exactly like
`organizations`/`members`: `lib/uml_documents.ts` (thin `apiFetch` wrappers, no
try/catch, `ApiError` reaches the caller verbatim) → `state/document.ts`
(`useDocument`, local `useState` mirroring `useMembers`) → `components/workspace/*`
(presentational, props-in/callback-out like `CreateOrgForm`) →
`app/(app)/documents/[docId]/page.tsx` (`"use client"` container reading
`activeOrgSlugAtom` via `useAtomValue`, like `settings/members/page.tsx`). Auth is
inherited from `(app)/layout.tsx`. `backend/` diff stays empty.

`DiagramCanvas` is the only genuinely new mechanism: a hand-rolled Cytoscape seam with
one mount effect (construct + `destroy`) and one revision-keyed update effect, plus a
pure `toElements(model)` mapper that carries all the domain knowledge and is testable
without a DOM.

## Decision Drivers

- Backend is frozen: `CommandResultOut` returns `{revision, validation}` only — never
  the updated model — and every `add_*` command requires a **caller-supplied element id**.
- `DocumentOut.model`/`.layout` are `dict` on the wire (no schema codegen), so TS types
  are hand-written and must be pinned to a real `codec._encode_model` output.
- No React-Cytoscape binding library is installed; lifecycle is hand-written.
- jsdom has no canvas — Cytoscape cannot really render under Vitest.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | Hand-written TS types in `lib/uml_documents.ts`, structurally typed all the way down (`UmlModel`, `UmlClass`, `UmlAttribute`, `Relationship`, `Multiplicity`), pinned to the concrete `_encode_model` fixture below | Mirror the backend and type `model`/`layout` as `unknown`/`Record<string, unknown>` | The backend uses `dict` only to avoid duplicating a Pydantic shape it already has in `codec.py`; the frontend has no such source, so an untyped blob would push `as` casts into `toElements`. The fixture is copied verbatim into the test suite so drift fails a test, not a runtime render (proposal Risk 2) |
| DD2 | `useDocument(docId)` holds `document`/`loading`/`error`/`lastValidation` in local `useState`, not a Jotai atom | Module-level `documentAtom` like `organizationsAtom` | Verbatim `useMembers` rationale: exactly one consumer (the `[docId]` container) and it must reset per document — a module atom would paint document A's classes for a frame after navigating to B. Uses the same render-time `trackedId !== docId` reset that `useMembers` uses for `orgSlug`, satisfying `react-hooks/set-state-in-effect` |
| DD3 | `submitCommand` POSTs, then `await getDocument(...)` and writes both the refetched document and the returned `CommandResultOut.validation` into state before resolving | Optimistic local mutation; refetch fired without awaiting | Confirmed user decision (exploration §Scope Decisions 3). Awaiting the refetch means the promise a form `await`s resolves only once the canvas is consistent, so forms keep `CreateOrgForm`'s "clear the inputs after `await onCreate(...)`" pattern unchanged. The POST's `revision` is *not* used to patch state — the GET is the single source |
| DD4 | Two separate effects in `DiagramCanvas`: mount effect `useEffect(..., [])` constructs `cytoscape({container: ref.current, ...})` and returns `() => cy.destroy()`; update effect `useEffect(..., [revision])` calls `cy.json({elements})` then `cy.layout({name: "fcose"}).run()` | One effect keyed on `elements`; re-create the instance per document change | An `elements`-keyed effect re-runs on every render (new array identity) and would re-layout mid-typing. `revision` is a monotonic server integer that changes exactly when the model changed, so it is the correct and cheapest dependency. `cy.json({elements})` diffs (adds/updates/removes) rather than rebuilding, preserving the instance and its handlers |
| DD5 | `cytoscape.use(fcose)` called once at module top level, guarded by nothing | Register inside the mount effect | `cytoscape.use` on an already-registered extension warns; module scope runs once per bundle. `cytoscape` ships first-party types (`index.d.ts`) and `@types/cytoscape-fcose` is already a devDependency — no new dependency (proposal §Dependencies) |
| DD6 | `toElements(model: UmlModel): ElementDefinition[]` is a pure exported function in `DiagramCanvas.tsx`'s own module, taking only the model | Build elements inline in the effect; put the mapper in `lib/` | Keeps the one piece of real domain logic in the canvas unit-testable with zero DOM and zero Cytoscape mock (see Testing Strategy). It belongs beside its only consumer, not in `lib/` which is reserved for HTTP clients in this codebase |
| DD7 | Attributes render inside the class node's own multi-line `label` (`Name\n──────\n- attr: Type`), with `"text-wrap": "wrap"` | Compound/child nodes per attribute; HTML overlay extension | UML class boxes are one visual unit; child nodes would make attributes independently tappable and break DD9's "tap a node = pick a class" invariant. No extension needed |
| DD8 | Relationship click-click state (`pendingSourceId`) lives in the **page container**, not in `DiagramCanvas`; the canvas exposes `onNodeTap(classId)` and a `highlightedClassId` prop | Track selection inside `DiagramCanvas`; use a Jotai atom | Keeps `DiagramCanvas` presentational like every other `components/workspace/*` file, and lets `AddRelationshipControl` render the "source selected, pick a target" affordance from the same state the canvas highlights |
| DD9 | The `tap` handler is bound **once** in the mount effect and calls through a `useRef` holding the latest `onNodeTap` (`onNodeTapRef.current?.(...)`) | Bind/unbind the handler in an effect keyed on `onNodeTap` | The mount effect's `[]` dependency list would otherwise capture the first render's closure and always see `pendingSourceId === null`. This is the specific stale-closure trap of a hand-rolled imperative seam; the ref indirection is the whole reason it is called out as a decision |
| DD10 | Element ids are generated client-side with `crypto.randomUUID()` at submit time | Let the backend assign ids | Not a choice: `AddClassIn.class_id`, `UmlAttributeIn.id` and `RelationshipIn.id` are all required request fields — the frozen command bus has no id-allocation path |
| DD11 | `page.tsx` stays `"use client"` and unwraps the Next 16 `params: Promise<{docId: string}>` with React's `use()` | `async function Page({params})` server component wrapping a client child | Verified against `node_modules/next/dist/docs/.../page.md`: `params` is a Promise in this version and must be unwrapped with `async/await` **or** `use()`. The page needs `useAtomValue(activeOrgSlugAtom)` and `useDocument`, so it must be a client component; `use()` is the sanctioned client unwrap and avoids inventing a two-file split this codebase has no precedent for |
| DD12 | Multiplicity crosses the wire as the UML **string** form (`"1"`, `"0..*"`) on the way in, and comes back as `{lower, upper}` on the way out | Send `{lower, upper}` | Asymmetric by backend design: `RelationshipEndIn.multiplicity` is `str` parsed by `parse_multiplicity`, while `codec._encode_multiplicity` emits the object. `formatMultiplicity({lower, upper})` in `lib/uml_documents.ts` mirrors backend `format_multiplicity` for the edge label |
| DD13 | Validation renders non-blockingly from `lastValidation`, which is `null` until the first command | Derive validation on load | `GET /documents/{id}` returns no `validation` field at all — only `POST .../commands` does. `ValidationPanel` therefore renders nothing before the first command, and after it renders every diagnostic regardless of `is_valid` (exploration §Scope Decisions 4) |
| DD14 | `CreateDocumentForm` receives `onCreate` and does the `router.push` itself in the container's handler, not in the form | Form owns `useRouter` | Mirrors `CreateOrgForm`: the form is props-in/callback-out and stays render-testable without a router mock; navigation belongs to the dashboard container, as in `useLeaveOrganization` |

## Data Flow

    AddClassForm / AddAttributeForm / AddRelationshipControl
         │ onSubmit(command)                    ▲ classes[] props
         ▼                                      │
    documents/[docId]/page.tsx  (container, "use client")
         │ useAtomValue(activeOrgSlugAtom) ──→ orgSlug
         │ submitCommand(command)
         ▼
    state/document.ts  useDocument(docId)
         │ 1. submitCommand(orgSlug, docId, command)  ──→ CommandResultOut
         │ 2. await getDocument(orgSlug, docId)       ──→ DocumentOut   (DD3)
         │ 3. setDocument(fresh); setLastValidation(result.validation)
         ▼
    document.model ──→ DiagramCanvas ──→ toElements() ──→ cy.json() + fcose  (DD4)
    lastValidation ──→ ValidationPanel                            (DD13)

    Node tap ──→ onNodeTap(classId) ──→ container pendingSourceId  (DD8/DD9)
                    null → "ClassA"  → second tap → AddRelationship command

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/lib/uml_documents.ts` | Create | TS types + `createDocument`/`getDocument`/`submitCommand` `apiFetch` wrappers, `formatMultiplicity` |
| `frontend/src/state/document.ts` | Create | `useDocument(docId)` — load, `submitCommand`, refetch |
| `frontend/src/components/workspace/DiagramCanvas.tsx` | Create | Cytoscape seam + exported pure `toElements` |
| `frontend/src/components/workspace/AddClassForm.tsx` | Create | Name input → `AddClass` |
| `frontend/src/components/workspace/AddAttributeForm.tsx` | Create | Class select + name + `PrimitiveType` select → `AddAttribute` |
| `frontend/src/components/workspace/AddRelationshipControl.tsx` | Create | Click-click prompt + multiplicity selects → `AddRelationship` |
| `frontend/src/components/workspace/ValidationPanel.tsx` | Create | Renders `Diagnostic[]`, non-blocking |
| `frontend/src/components/workspace/CreateDocumentForm.tsx` | Create | Name input → `onCreate` |
| `frontend/src/app/(app)/documents/[docId]/page.tsx` | Create | Container; first dynamic route segment |
| `frontend/src/app/(app)/dashboard/page.tsx` | Modify | Render `<CreateDocumentForm>` when `activeOrg` exists; handler does `createDocument` + `router.push(/documents/${doc.id})` |
| `frontend/src/**/__tests__/*` | Create | Vitest + RTL per module (see Testing Strategy) |
| `backend/**` | **None** | Zero diff — confirmed |

## Interfaces / Contracts

### Pinned wire fixture (DD1)

Verbatim `_document_out(...)` output for a document with one class, one attribute and
one relationship — reused as the test fixture:

```json
{
  "id": "6f1c2e2a-0000-4000-8000-000000000001",
  "owner_id": "1",
  "revision": 4,
  "metadata": { "name": "Ventas", "description": "" },
  "model": {
    "classes": [
      { "id": "c1", "name": "Cliente", "visibility": "public",
        "attributes": [{ "id": "a1", "name": "nombre", "type": "String", "visibility": "private" }],
        "operations": [] }
    ],
    "enumerations": [],
    "relationships": [
      { "id": "r1", "kind": "association",
        "source": { "class_id": "c1", "multiplicity": { "lower": 1, "upper": 1 }, "role": null },
        "target": { "class_id": "c2", "multiplicity": { "lower": 0, "upper": null }, "role": null },
        "name": null }
    ],
    "generation_metadata": {}
  },
  "layout": { "positions": {} },
  "created_at": "2026-09-12T10:00:00Z",
  "updated_at": "2026-09-12T10:05:00Z"
}
```

### `lib/uml_documents.ts`

```ts
export type PrimitiveType =
  | "String" | "Text" | "Integer" | "Long" | "Decimal" | "Boolean" | "Date" | "DateTime";
export const PRIMITIVE_TYPES: readonly PrimitiveType[] = [/* the eight above */];

export type EnumerationRef = { enumeration_ref: { enumeration_id: string } };
export type AttributeType = PrimitiveType | EnumerationRef;   // str vs. dict, per codec DD7
export type Visibility = "public" | "private" | "protected" | "package";

export type UmlAttribute = { id: string; name: string; type: AttributeType; visibility: Visibility };
export type UmlOperation = {
  id: string; name: string; return_type: AttributeType | null;
  parameters: { name: string; type: AttributeType }[]; visibility: Visibility;
};
export type UmlClass = {
  id: string; name: string; visibility: Visibility;
  attributes: UmlAttribute[]; operations: UmlOperation[];
};
export type Multiplicity = { lower: number; upper: number | null };   // upper null === "*"
export type RelationshipEnd = { class_id: string; multiplicity: Multiplicity; role: string | null };
export type RelationshipKind = "association" | "aggregation" | "composition" | "generalization";
export type Relationship = {
  id: string; kind: RelationshipKind;
  source: RelationshipEnd; target: RelationshipEnd; name: string | null;
};
export type UmlModel = {
  classes: UmlClass[];
  enumerations: { id: string; name: string; literals: { id: string; name: string; value: string }[] }[];
  relationships: Relationship[];
  generation_metadata: Record<string, unknown>;
};
export type DiagramLayout = { positions: Record<string, { x: number; y: number }> };

export type UmlDocument = {
  id: string; owner_id: string; revision: number;
  metadata: { name: string; description: string };
  model: UmlModel; layout: DiagramLayout;
  created_at: string; updated_at: string;
};

export type Diagnostic = { severity: "error" | "warning"; code: string; message: string; path: string };
export type CommandResult = { revision: number; validation: { is_valid: boolean; violations: Diagnostic[] } };

// Only the three command shapes this cycle submits (the other four exist backend-side
// but are out of scope — proposal §Out of Scope).
export type UmlCommandIn =
  | { type: "AddClass"; class_id: string; name: string }
  | { type: "AddAttribute"; class_id: string; attribute: { id: string; name: string; type: AttributeType; visibility?: Visibility } }
  | { type: "AddRelationship"; relationship: {
      id: string; kind: "association"; name?: string | null;
      // NOTE DD12: multiplicity goes OUT as a UML string, comes BACK as {lower, upper}
      source: { class_id: string; multiplicity: string; role?: string | null };
      target: { class_id: string; multiplicity: string; role?: string | null };
    } };

const base = (orgSlug: string) => `/api/orgs/${encodeURIComponent(orgSlug)}/documents`;

export async function createDocument(orgSlug: string, input: { name: string }): Promise<UmlDocument>;
export async function getDocument(orgSlug: string, docId: string): Promise<UmlDocument>;
export async function submitCommand(orgSlug: string, docId: string, command: UmlCommandIn): Promise<CommandResult>;

export function formatMultiplicity(m: Multiplicity): string;  // mirrors backend format_multiplicity
export function attributeTypeLabel(t: AttributeType): string;  // string → itself; ref → enum id
```

All three are one-line `apiFetch` calls with no try/catch (verbatim `lib/organizations.ts`
convention), so `ApiError` — including the 403 from `require_role` and the 422
`invalid_command_payload` — reaches the caller unchanged.

### `state/document.ts`

```ts
export function useDocument(orgSlug: string | null, docId: string) {
  const [document, setDocument] = useState<UmlDocument | null>(null);
  const [loading, setLoading] = useState(orgSlug !== null);
  const [error, setError] = useState<string | null>(null);
  const [lastValidation, setLastValidation] = useState<CommandResult["validation"] | null>(null);
  const [tracked, setTracked] = useState(`${orgSlug}:${docId}`);   // render-time reset, DD2

  // effect: idle while orgSlug === null; getDocument(...).then/catch/finally with a
  // `cancelled` flag — verbatim useMembers shape, deps [orgSlug, docId].

  const submitCommand = useCallback(async (command: UmlCommandIn) => {
    if (orgSlug === null) throw new Error("No active organization");
    const result = await submitCommandApi(orgSlug, docId, command);   // rethrows verbatim
    setDocument(await getDocumentApi(orgSlug, docId));                 // DD3
    setLastValidation(result.validation);
    return result;
  }, [orgSlug, docId]);

  return { document, loading, error, lastValidation, submitCommand };
}
```

### `DiagramCanvas.tsx`

```tsx
cytoscape.use(fcose);                                    // module scope, DD5

export function toElements(model: UmlModel): ElementDefinition[] {   // pure, DD6
  const nodes = model.classes.map((c) => ({
    data: { id: c.id, label: [c.name, "──────", ...c.attributes.map(
      (a) => `- ${a.name}: ${attributeTypeLabel(a.type)}`)].join("\n") },
  }));
  const known = new Set(model.classes.map((c) => c.id));
  const edges = model.relationships
    .filter((r) => known.has(r.source.class_id) && known.has(r.target.class_id))
    .map((r) => ({ data: {
      id: r.id, source: r.source.class_id, target: r.target.class_id,
      label: `${formatMultiplicity(r.source.multiplicity)} → ${formatMultiplicity(r.target.multiplicity)}`,
    }}));
  return [...nodes, ...edges];
}

type Props = { model: UmlModel; revision: number;
               onNodeTap?: (classId: string) => void; highlightedClassId?: string | null };

const containerRef = useRef<HTMLDivElement>(null);
const cyRef = useRef<cytoscape.Core | null>(null);
const onNodeTapRef = useRef(onNodeTap);
onNodeTapRef.current = onNodeTap;                        // DD9: latest callback, no rebind

useEffect(() => {                                        // MOUNT — runs once, DD4
  const cy = cytoscape({ container: containerRef.current!, elements: [], style: STYLE });
  cy.on("tap", "node", (e) => onNodeTapRef.current?.(e.target.id()));
  cyRef.current = cy;
  return () => { cy.destroy(); cyRef.current = null; };
}, []);

useEffect(() => {                                        // UPDATE — revision-keyed, DD4
  const cy = cyRef.current;
  if (!cy) return;
  cy.json({ elements: toElements(model) });              // diffing add/update/remove
  cy.layout({ name: "fcose", animate: false }).run();
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [revision]);

useEffect(() => {                                        // highlight only — no re-layout
  cyRef.current?.nodes().removeClass("selected-source");
  if (highlightedClassId) cyRef.current?.getElementById(highlightedClassId).addClass("selected-source");
}, [highlightedClassId]);
```

`model` is deliberately excluded from the update effect's deps (DD4): `revision` is the
server's own change marker and `model` gets a fresh identity on every refetch.

### Click-click relationship (DD8) — container-owned

```
pendingSourceId: string | null      // useState in documents/[docId]/page.tsx

handleNodeTap(classId):
  if pendingSourceId === null        → setPendingSourceId(classId)        // "source selected"
  else if classId === pendingSourceId → setPendingSourceId(null)          // tap again = cancel
  else                                → setPendingTargetId(classId)       // both ends chosen
```

`AddRelationshipControl` receives `{pendingSourceId, pendingTargetId, classes, onSubmit,
onCancel}`, renders the two multiplicity selects (`"1" | "0..1" | "0..*" | "1..*"`, DD12)
and calls `onSubmit`, which builds the command with `crypto.randomUUID()` (DD10) and
clears both ids on success.

### `documents/[docId]/page.tsx` (DD11)

```tsx
"use client";
export default function DocumentPage({ params }: { params: Promise<{ docId: string }> }) {
  const { docId } = use(params);
  const orgSlug = useAtomValue(activeOrgSlugAtom);
  const { document, loading, error, lastValidation, submitCommand } = useDocument(orgSlug, docId);
  ...
}
```

Renders the same `activeSlug === null` guard copy as `settings/members/page.tsx`.
UI strings stay Spanish, matching every existing `components/workspace/*` file.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit — `lib/uml_documents.ts` | Each wrapper hits the right path/method/body; `ApiError` propagates; `formatMultiplicity` covers `1`/`0..1`/`0..*` | `vi.mock("@/lib/api")` + `vi.mocked(apiFetch)`, mirroring `lib/__tests__/organizations.test.ts` |
| Unit — `toElements` | Pinned fixture → expected nodes/edges; attribute lines in the label; `EnumerationRef` type renders; edge whose endpoint class is missing is dropped | Plain Vitest — **no DOM, no Cytoscape instance** (the whole point of DD6) |
| Unit — `useDocument` | Loads on mount; resets when `docId` changes; `submitCommand` calls POST **then** GET in that order and stores `validation`; a rejected POST leaves `document` untouched and rethrows | `renderHook` + `vi.mock("@/lib/uml_documents")`, verbatim `state/__tests__/members.test.ts` shape |
| Component | `AddClassForm`/`AddAttributeForm`/`CreateDocumentForm` submit the right payload and clear on success; `ValidationPanel` renders both severities and nothing when `null`; `AddRelationshipControl` renders the pending-source prompt | RTL, mirroring `CreateOrgForm.test.tsx` |
| Component — `DiagramCanvas` | Constructs once, `destroy()` on unmount, `json`+`layout` called on revision change and **not** on an unrelated re-render, `tap` handler routes to the latest `onNodeTap` | `vi.mock("cytoscape")` returning a fake `Core` — jsdom has no canvas, so a real instance cannot render; assertions are on the mock's call log |
| Container | `documents/[docId]/page.tsx` renders classes count + panels; click-click state machine (tap A → tap A cancels; tap A → tap B opens the control) | RTL with `useDocument` mocked |
| E2E | Deferred — no E2E harness exists in this repo | — |

## Threat Matrix

N/A — no routing decisions from untrusted input, shell, subprocess, VCS/PR automation,
executable-file classification, or process integration. This is browser-side rendering
over an already-authenticated, already-CSRF-protected `apiFetch` seam; `docId` is passed
to `encodeURIComponent` and resolved server-side by a tenant-scoped `UUID` lookup.

## Migration / Rollout

No migration. Purely additive frontend files plus one dynamic route segment and one
block in `dashboard/page.tsx`; rollback is deleting them (proposal §Rollback Plan).

## Open Questions

- [ ] Relationship `name`/`role` are never collected this cycle (both sent as `null`) —
      the backend accepts it, but `sdd-spec` may want an explicit scenario saying so.
- [ ] The fcose layout re-runs on **every** revision change, so adding one class
      reflows the whole graph. Acceptable while layout is ephemeral (exploration
      §Scope Decisions 2); would need `{fit: false, randomize: false}` tuning or real
      layout persistence the moment a backend position command exists.

> Size note: exceeds the skill's 800-word soft budget for the same reason the
> `uml-document-persistence` design did — the task required field-level type and
> lifecycle detail sufficient for `sdd-tasks` to slice units without re-deriving the
> Cytoscape seam or the wire shapes.
