# Design: UML Generation Profile Panel

## Summary

Add one frontend-only authoring surface for existing UML generation profile metadata. The implementation will extend the frontend command union, mount a new sidebar Card on the UML document page, and add a presentational panel that pre-fills tri-state controls from `generation_metadata` and submits `SetGenerationProfile` through the existing REST `submitCommand` flow.

This design intentionally does not change backend behavior, persistence, canvas rendering, WebSocket messages, generated code, Flutter/mobile, or `defaultSort` authoring.

## File change plan

| Path | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/lib/uml_documents.ts` | Modify | Add the `SetGenerationProfile` variant to `UmlCommandIn`: `{ type: "SetGenerationProfile"; element_id: string; profile: Record<string, unknown> | null }`. Keep the REST `submitCommand` implementation unchanged so this command is forwarded like every other `UmlCommandIn`. |
| `frontend/src/components/workspace/GenerationProfilePanel.tsx` | Create | Presentational form for target selection, safe prefill, tri-state controls, payload building, `submitCommand` dispatch, Spanish error display, and local state reconciliation after success. |
| `frontend/src/app/(app)/documents/[docId]/page.tsx` | Modify | Import `GenerationProfilePanel` and add one Card titled `Perfil de generación` in the existing `<aside>` sidebar, preferably between `ValidationPanel` and the `Agregar` group. Pass `document.model.classes`, `document.model.generation_metadata`, `submitCommand`, and `isSubmitting`. |
| `frontend/src/components/workspace/__tests__/GenerationProfilePanel.test.tsx` | Create | Component tests for target listing, prefill, malformed metadata, declared-only submit payloads, clear behavior, CRUD mapping, success state update, and 422 error display. |
| `frontend/src/lib/__tests__/uml_documents.test.ts` | Modify | Add a forwarding/type coverage test proving `submitCommand` accepts and forwards `SetGenerationProfile` verbatim. |

## Interfaces and contracts

### Frontend command type

`frontend/src/lib/uml_documents.ts` should extend `UmlCommandIn` with exactly this variant:

```ts
| { type: "SetGenerationProfile"; element_id: string; profile: Record<string, unknown> | null }
```

No semantic profile type should be duplicated in the API client. The backend remains the semantic authority for accepted profile shapes.

### Panel props

`GenerationProfilePanel` should receive:

```ts
type GenerationProfilePanelProps = {
  classes: UmlClass[];
  generationMetadata: UmlModel["generation_metadata"];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};
```

The component remains presentational and should not call document hooks directly.

## UI placement

In `frontend/src/app/(app)/documents/[docId]/page.tsx`, add a new sidebar section/card after `ValidationPanel` and before mutation groups:

- Card title: `Perfil de generación`.
- Card content: `GenerationProfilePanel`.
- Props:
  - `classes={document.model.classes}`
  - `generationMetadata={document.model.generation_metadata}`
  - `onSubmit={submitCommand}`
  - `disabled={isSubmitting}`

This keeps generation-profile editing near validation feedback and avoids mixing it into the add/remove command groups.

## Target model

The panel derives selectable targets from `classes` on every render:

- Class target option: `{ kind: "class", elementId: class.id, label: `Clase: ${class.name}` }`.
- Attribute target option: `{ kind: "attribute", elementId: attribute.id, classId: class.id, label: `Atributo: ${class.name}.${attribute.name}` }`.

The selected target kind must be resolved from this derived list, not trusted from stale local state. If a refetch removes the selected element, the effective selection collapses to no selection and submit is disabled.

## Tri-state control choice

Use the existing `Select` UI component from `frontend/src/components/ui/select.tsx` for each tri-state field.

Reason:

- The project currently has no custom radio group, segmented control, switch, or toggle component.
- `Select` is already used by workspace controls and keeps the slice small.
- It can represent all three states explicitly with Spanish labels.

Each tri-state select should use this local state vocabulary:

```ts
type TriState = "unset" | "true" | "false";
```

Suggested labels:

- `unset`: `Sin declarar`
- `true`: `Sí`
- `false`: `No`

Visible controls:

- Class targets: `auditable`, `readOnly`, `crud`.
- Attribute targets: `searchable`, `sortable`, `readOnly`.

No `defaultSort`, relationship, operation, or extra profile keys are included in this slice.

## Prefill logic from generation_metadata

When the selected target changes, recompute the visible tri-state state from:

```ts
generationMetadata[elementId].profile
```

Runtime guards are required because `generation_metadata` is typed as `Record<string, unknown>`:

1. Read `entry = generationMetadata[elementId]`.
2. Treat `entry` as usable only if it is a non-null object and not an array.
3. Read `profile = entry.profile`.
4. Treat `profile` as usable only if it is a non-null object and not an array.
5. Missing, `null`, arrays, primitives, or malformed shapes produce all visible controls as `"unset"`.

Boolean fields prefill as follows:

- `true` -> `"true"`.
- `false` -> `"false"`.
- anything else -> `"unset"`.

`crud` prefill for class targets:

- `crud` equal to an array containing all four operations `create`, `read`, `update`, and `delete` -> `"true"`.
- `crud` equal to an empty array -> `"false"`.
- any other value or partial array -> `"unset"`.

This avoids claiming unsupported semantics for partial CRUD arrays in the first UI slice.

## Submit payload building

On form submit:

1. Resolve the current selected target from the derived target list.
2. If there is no valid target, do nothing.
3. Build a plain profile object containing only declared controls.
4. For boolean controls:
   - `"true"` -> include `key: true`.
   - `"false"` -> include `key: false`.
   - `"unset"` -> omit the key.
5. For class `crud`:
   - `"true"` -> include `crud: ["create", "read", "update", "delete"]`.
   - `"false"` -> include `crud: []`.
   - `"unset"` -> omit `crud`.
6. If the profile object has no keys, submit `profile: null` to clear the profile.
7. Dispatch exactly one command through the injected submit callback:

```ts
await onSubmit({
  type: "SetGenerationProfile",
  element_id: selectedTarget.elementId,
  profile,
});
```

The implementation must not send raw boolean `crud` values.

## Local state update on success

After `onSubmit` resolves successfully:

- Clear any previous error.
- Keep the selected target selected.
- Normalize the visible local tri-state controls to the values that were just submitted.
- If the submitted payload was `profile: null`, set all visible controls to `"unset"`.

This gives immediate UI confirmation even before the post-command refetch or WebSocket update converges the document state.

If `onSubmit` rejects:

- Preserve the current local form values.
- Display `err.detail` when `err instanceof ApiError`.
- Otherwise display `Ocurrió un error inesperado. Intenta de nuevo.`
- Keep the panel mounted.

## Data flow

1. `DocumentPage` obtains `document`, `isSubmitting`, and `submitCommand` from `useDocument(orgSlug, docId)`.
2. `DocumentPage` passes `classes`, `generation_metadata`, `submitCommand`, and disabled state into `GenerationProfilePanel`.
3. `GenerationProfilePanel` derives class and attribute targets from `classes`.
4. User selects a target.
5. Panel safely reads `generationMetadata[target.elementId].profile` and pre-fills the visible tri-state controls.
6. User edits tri-state controls.
7. User submits.
8. Panel builds a declared-only profile object or `null`.
9. Panel calls `onSubmit` with `SetGenerationProfile`.
10. `useDocument(...).submitCommand` sends the existing REST POST, validates the command result shape, refetches the document, and updates document/validation state.
11. Panel normalizes local state to the submitted values after successful resolution.

## Error handling and edge cases

- No classes: render an empty target select state and disable submit.
- Selected target removed by refetch: derive effective selection as invalid and disable submit.
- Attribute IDs are displayed with class context to avoid ambiguity.
- Unknown or malformed `generation_metadata` never crashes the component.
- Backend 422 remains authoritative and is shown through `ApiError.detail`.
- Concurrent edits remain current last-writer-wins command behavior; this slice does not add base-revision conflict handling.

## Test plan

### `frontend/src/lib/__tests__/uml_documents.test.ts`

- Add `submitCommand forwards SetGenerationProfile verbatim as the JSON body`:
  - command: `{ type: "SetGenerationProfile", element_id: "c1", profile: { readOnly: true } }`.
  - expect `apiFetch` POST body `json` equals that command.

### `frontend/src/components/workspace/__tests__/GenerationProfilePanel.test.tsx`

Cover these cases with React Testing Library and Vitest:

1. Renders class and attribute target options from `classes`.
2. Selecting a class shows only `auditable`, `readOnly`, and `crud` controls.
3. Selecting an attribute shows only `searchable`, `sortable`, and `readOnly` controls.
4. Class profile prefill maps `{ auditable: true, readOnly: false, crud: ["create", "read", "update", "delete"] }` to true/false/true controls.
5. Attribute profile prefill maps `{ searchable: true, sortable: false, readOnly: true }` to true/false/true controls.
6. Changing selection replaces old control values with the newly selected element's profile values.
7. Missing, null, array, primitive, or malformed profile metadata pre-fills all visible controls as unset.
8. Declared class controls submit `{ type: "SetGenerationProfile", element_id, profile: { auditable: true, crud: [] } }` when `auditable=true`, `readOnly=unset`, `crud=false`.
9. Declared attribute controls submit `{ searchable: true, readOnly: false }` and omit `sortable` when unset.
10. All controls unset submits `profile: null`.
11. `crud=true` submits `crud: ["create", "read", "update", "delete"]`, never a boolean.
12. Successful submit keeps the target selected and normalizes visible local controls to the submitted values.
13. Rejected submit with `ApiError({ status: 422, detail: "..." })` displays the backend detail and keeps the form rendered.

### Optional page coverage

Only add a page-level test if existing page tests already assert exact sidebar contents. Otherwise, component coverage plus the lib forwarding test is sufficient for this bounded slice.

## Rollout and rollback

Rollout is a frontend-only additive change. Deploying it exposes an already supported backend command through the document sidebar.

Rollback is a frontend revert of:

- the `UmlCommandIn` variant,
- `GenerationProfilePanel.tsx`,
- the new sidebar Card import/render,
- related tests.

Stored `generation_metadata` remains valid because backend storage and command behavior are unchanged.

## Review boundary

The expected implementation should remain below the 400 changed-line review budget if it is kept to one component, one command union addition, one page mount, and focused tests. If implementation expands into custom UI primitives, page-wide restructuring, backend validation, `defaultSort`, or generated-code behavior, pause under the `ask-on-risk` delivery strategy before continuing.
