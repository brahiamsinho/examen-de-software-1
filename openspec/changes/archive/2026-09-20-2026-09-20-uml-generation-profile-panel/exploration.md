# Exploration: 2026-09-20-uml-generation-profile-panel

Read-only exploration for frontend slice 2 of the generation profile authoring path. Goal: add a sidebar Card titled **Perfil de generación** with tri-state controls prefilled from `model.generation_metadata`, and submit `SetGenerationProfile` commands through the existing command API. No code was changed.

## Scope from preflight

- Execution mode: auto.
- Artifact store: OpenSpec.
- Delivery strategy: ask-on-risk, review budget 400 changed lines.
- Backend slice is already done: `SetGenerationProfile` exists server-side and is pushed/available to target from the frontend.
- This exploration defines a bounded first frontend slice only; no commit and no implementation in this phase.

## Existing frontend sidebar structure

- Main document screen: `frontend/src/app/(app)/documents/[docId]/page.tsx`.
- The page is a client component that reads `orgSlug`, calls `useDocument(orgSlug, docId)`, renders `DiagramCanvas`, `ValidationPanel`, and an `<aside className="... lg:w-96 ...">` stack.
- Current sidebar groups:
  - `ValidationPanel lastValidation={lastValidation}`.
  - `Agregar` group with Card-wrapped `AddClassForm`, `AddAttributeForm`, `AddOperationForm`, plus `AddRelationshipControl`.
  - `Eliminar` group with Card-wrapped `RemoveClassControl`, `RemoveAttributeControl`, `RemoveOperationControl`, `RemoveRelationshipControl`.
- Sidebar Card pattern uses `frontend/src/components/ui/card.tsx` plus presentational workspace controls under `frontend/src/components/workspace/`.
- Controls are generally presentational, receive `classes`, `relationships` if needed, `onSubmit={submitCommand}`, and `disabled={isSubmitting}`. Each handles local submit/error state and translates `ApiError.detail` into Spanish UI copy.

## Existing command dispatch path

- Commands are sent over REST, not WebSocket.
- `frontend/src/lib/uml_documents.ts` exposes `submitCommand(orgSlug, docId, command)` which POSTs to `/api/orgs/{slug}/documents/{docId}/commands` using `apiFetch` with `{ method: "POST", json: command }`.
- `frontend/src/state/document.ts` exposes `useDocument(...).submitCommand`, which:
  1. calls the REST `submitCommandApi`,
  2. runtime-checks the `CommandResult` shape,
  3. refetches the full document with `getDocumentApi`,
  4. stores `lastValidation`,
  5. preserves the previous document if the POST fails or response is malformed.
- WebSocket integration in `openDocumentSocket` and `useDocument` is for document broadcasts and node lock/position frames. It receives `document.update`, `node.locked`, `node.unlocked`, `node.position`, `node.locks`, and `node.claim_rejected`; command envelopes are not sent over WS.
- The modeling canvas receives `model`, `revision`, `layout`, lock refs, and node gesture callbacks. It does not dispatch profile commands and does not currently read `generation_metadata`.

## Backend generation_metadata and SetGenerationProfile shape

- Backend codec (`backend/apps/uml_documents/codec.py`) encodes `CanonicalUmlModel.generation_metadata` verbatim as an object keyed by element id and decodes it back to `ElementId` keys.
- Wire shape in the frontend is currently `UmlModel.generation_metadata: Record<string, unknown>`.
- Relevant metadata shape for this feature is `generation_metadata[elementId] == { profile: { ... }, ...siblings }`.
- The command owns only the `profile` key. Sibling keys such as `source` or `confidence` are preserved server-side.
- `backend/apps/uml_documents/schemas.py` defines `SetGenerationProfileIn` as `{ type: "SetGenerationProfile"; element_id: str; profile: dict | None = None }`; absent, `null`, and `{}` all clear.
- `backend/apps/uml_documents/services.py` validates `SetGenerationProfile` inside the row lock before apply. Unknown element ids are 422, even for clear. Non-empty profile bodies are parsed strictly with the generation profile parser. `defaultSort.attribute` must resolve to an allowed attribute.

## Current TypeScript command types

- `frontend/src/lib/uml_documents.ts` has `UmlCommandIn` with 8 variants: `AddClass`, `AddAttribute`, `AddOperation`, `AddRelationship`, `RemoveClass`, `RemoveAttribute`, `RemoveOperation`, `RemoveRelationship`.
- `RenameClass` remains intentionally unwired in the UI.
- `SetGenerationProfile` is not yet present in `UmlCommandIn`, so the frontend cannot type-check profile command submission until this union is extended.
- Minimal type addition for the slice should be a raw JSON-native profile body type, not a full semantic duplicate of backend validation. A narrow local union/type for profile keys can exist for UI state, but the command should remain structurally compatible with backend: `{ type: "SetGenerationProfile"; element_id: string; profile: Record<string, unknown> | null }`.

## UI model for tri-state controls

The profile semantics require tri-state booleans because absent means undeclared and differs from `false`.

### Table-level controls for classes

- `entity`: unset / true / false.
- `auditable`: unset / true / false.
- `readOnly`: unset / true / false.
- `crud`: subset of `create`, `read`, `update`, `delete`; out-of-scope for tri-state but part of existing backend vocabulary. Keep bounded by simple checkboxes or defer if line budget risk appears.
- `defaultSort`: optional attribute + direction (`asc`/`desc`). First slice may include only own class attributes if it wants to avoid reproducing descendant resolution in UI; backend remains final authority.

### Column-level controls for attributes

- `searchable`: unset / true / false.
- `sortable`: unset / true / false.
- `readOnly`: unset / true / false.

### Prefill

- Read from `document.model.generation_metadata[selectedElementId]`.
- Treat an entry as usable only when it is a non-null object and its `profile` key is a non-null object. Unknown/malformed shapes should degrade to all controls unset rather than crashing.
- Preserve no sibling keys client-side; just send the new `profile` body. Server preserves siblings by owning only the `profile` key.

## Candidate component design

Add one presentational component:

- `frontend/src/components/workspace/GenerationProfilePanel.tsx`
- Props:
  - `classes: UmlClass[]`
  - `generationMetadata: UmlModel["generation_metadata"]`
  - `onSubmit: (command: UmlCommandIn) => Promise<CommandResult>`
  - `disabled?: boolean`
- Responsibilities:
  - choose target element: a select that offers class-level and attribute-level options, e.g. `Clase: Cliente` and `Atributo: Cliente.nombre`.
  - derive selected element kind (`class` vs `attribute`) from `classes`, not from stored UI state alone.
  - prefill local form state when selected target changes, based on `generationMetadata`.
  - build a profile object containing only declared controls; if no controls are declared, send `profile: null` (or `{}`) to clear.
  - call `onSubmit({ type: "SetGenerationProfile", element_id, profile })`.
  - surface `ApiError.detail` in the same Alert pattern used by existing controls.

Integrate in `DocumentPage` by adding a new Card in the existing document sidebar, likely between `ValidationPanel` and `Agregar`, or as its own group above mutation groups:

- `CardTitle`: `Perfil de generación`.
- Pass `classes={document.model.classes}`, `generationMetadata={document.model.generation_metadata}`, `onSubmit={submitCommand}`, `disabled={isSubmitting}`.

## Testing seams

- Add component tests under `frontend/src/components/workspace/__tests__/GenerationProfilePanel.test.tsx`.
- Test cases for first slice:
  1. renders class and attribute target options.
  2. pre-fills class tri-state values from `{ [classId]: { profile: { auditable: true, readOnly: false } } }`.
  3. pre-fills attribute tri-state values from `{ [attributeId]: { profile: { searchable: true, sortable: false } } }`.
  4. submits `SetGenerationProfile` with only declared keys.
  5. submits `profile: null` when every control is unset.
  6. shows `ApiError.detail` on 422 and keeps the form rendered.
- Extend `frontend/src/lib/__tests__/uml_documents.test.ts` with a forwarding test for `SetGenerationProfile` once `UmlCommandIn` includes it.
- Optionally update `frontend/src/app/(app)/documents/[docId]/__tests__/page.test.tsx` only if existing page tests assert exact sidebar content; otherwise component-level coverage should keep the slice smaller.

## Risks and constraints

- Review budget: likely under 400 changed lines if the first slice is limited to one component, one command union addition, one lib test, one component test, and one page import/render. Adding full `crud` and `defaultSort` UI may push the slice toward the 400-line ask-on-risk gate.
- Do not duplicate backend semantic validation. The frontend should not try to enforce every parser rule; it should only build the known UI shapes and display server 422 details.
- `generation_metadata` is typed as `Record<string, unknown>`; runtime guards are needed before reading `profile`.
- `defaultSort` is the riskiest UI part because backend allows descendant attributes for inheritance roots. A bounded first slice can defer defaultSort or offer only own attributes with server validation as authority.
- Last-writer-wins still applies; there is no base revision check in command submission.
- Existing UI copy is Spanish and should remain Spanish.

## Bounded first slice recommendation

Implement only:

1. Extend `UmlCommandIn` with `SetGenerationProfile`.
2. Add `GenerationProfilePanel` with target selector and tri-state boolean controls.
3. Support table booleans (`entity`, `auditable`, `readOnly`) and attribute booleans (`searchable`, `sortable`, `readOnly`).
4. Prefill from existing `generation_metadata[*].profile` using safe runtime guards.
5. Submit `profile` with declared booleans only, or `null` to clear when all are unset.
6. Add the new Card to `DocumentPage` sidebar.
7. Add focused Vitest coverage for prefill and command submission.

Explicitly defer from this first slice:

- `crud` UI.
- `defaultSort` UI.
- client-side semantic validation beyond existing form/control shape and server error display.
- persistence changes, backend changes, WebSocket protocol changes, canvas rendering changes, and generation behavior changes.
