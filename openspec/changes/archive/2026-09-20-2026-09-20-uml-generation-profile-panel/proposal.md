# Proposal: UML Generation Profile Panel

## Intent

Add the first frontend authoring surface for the existing UML generation profile metadata. The backend already accepts `SetGenerationProfile` through the command endpoint; this change lets an editor choose a class or attribute in the document sidebar, review any existing declared profile values, and submit a profile update through the same REST `submitCommand` flow used by the other UML controls.

This is intentionally a frontend-only slice. It exposes the existing backend capability without changing generation rules, persistence, canvas rendering, validation semantics, WebSocket behavior, or Flutter.

## Scope

### In scope

- Extend the frontend `UmlCommandIn` TypeScript union with the backend command shape:
  - `{ type: "SetGenerationProfile"; element_id: string; profile: Record<string, unknown> | null }`.
- Add one sidebar Card titled **Perfil de generación** on the UML document page.
- Add a presentational `GenerationProfilePanel`-style control that:
  - lists class and attribute targets from the loaded document model;
  - derives target kind from the current `classes` array;
  - safely pre-fills from `document.model.generation_metadata[elementId].profile` when it is an object;
  - degrades malformed or unknown metadata shapes to all controls unset rather than crashing;
  - sends `SetGenerationProfile` through the existing `useDocument(...).submitCommand` REST path.
- Provide tri-state controls where unset means undeclared and differs from explicit `false`:
  - attribute targets: `searchable`, `sortable`, `readOnly`;
  - class targets: `auditable`, `readOnly`, `crud`.
- Map the `crud` tri-state UI to the existing backend profile vocabulary rather than sending a raw boolean:
  - unset: omit `crud`;
  - true: send `crud: ["create", "read", "update", "delete"]`;
  - false: send `crud: []`.
- Build profile payloads with declared controls only; if no controls are declared, submit `profile: null` to clear the profile.
- Surface backend `ApiError.detail` / 422 validation messages in the existing Spanish UI style.
- Add focused frontend tests for type forwarding, prefill, declared-only payload building, clear behavior, and error display.

### Out of scope

- `defaultSort` authoring.
- Backend changes.
- Persistence changes.
- Canvas behavior or canvas rendering changes.
- WebSocket protocol changes.
- New semantic validation beyond preexisting form shape and backend error display.
- Generated Spring/Next/Domain Manifest behavior changes.
- Flutter/mobile changes.
- Relationship-level or operation-level profile authoring.
- New profile keys outside the bounded controls above.

## Product outcome

Editors can declare generation intent directly where they already edit UML documents. A class or attribute can be marked as searchable, sortable, auditable, read-only, or CRUD-enabled/disabled without leaving the diagram page, and the saved metadata can continue through the already implemented backend and generation pipeline.

## Current-state gap

The backend profile command exists, but the frontend command union and sidebar do not expose it. As a result, users cannot author the declared generation profile from the UI even though `generation_metadata` can already carry it and the backend can validate it.

## Affected areas

| Area | Impact |
|------|--------|
| `frontend/src/lib/uml_documents.ts` | Add `SetGenerationProfile` to `UmlCommandIn`; optionally add narrow helper types for JSON profile payloads. |
| `frontend/src/components/workspace/GenerationProfilePanel.tsx` | New presentational panel for target selection, tri-state state, prefill, payload building, submit, and error display. |
| `frontend/src/app/(app)/documents/[docId]/page.tsx` | Add the **Perfil de generación** Card to the existing sidebar and pass `classes`, `generation_metadata`, `submitCommand`, and `isSubmitting`. |
| Frontend tests | Add component tests and a command-forwarding/type coverage test. |

## Approach

Keep the frontend thin and structural:

1. Treat `generation_metadata` as untrusted `Record<string, unknown>` and guard every read.
2. Use the selected element id plus the current document classes to determine whether class-level or attribute-level controls should render.
3. Represent each tri-state control locally as `"unset" | "true" | "false"`.
4. Convert local state to a JSON profile immediately before submit.
5. Submit exactly one `SetGenerationProfile` command via the existing REST command path.
6. Let the backend parser remain the semantic authority for accepted profile shapes.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `crud` is list-shaped in the backend but requested as a tri-state UI control. | Medium | Map the tri-state UI to the existing list vocabulary; do not send a boolean. |
| Malformed `generation_metadata` can crash a naive panel. | Medium | Use runtime guards and fall back to unset controls. |
| The panel duplicates backend validation rules. | Medium | Avoid semantic validation; only construct known UI shapes and show server errors. |
| Sidebar scope grows beyond the review budget. | Low/Medium | Keep the slice to one component, one type addition, one page mount, and focused tests; keep `defaultSort` excluded. |
| Concurrent edits remain last-writer-wins. | Medium | Accept current command behavior; WebSocket/refetch keeps clients converged after accepted commands. |

## Rollback plan

Revert the frontend change. Because this slice is additive and uses the existing backend command endpoint, rollback only removes the UI and TypeScript command variant; existing stored `generation_metadata` remains valid and backend behavior is unchanged.

## Success criteria

- [ ] `UmlCommandIn` accepts `SetGenerationProfile` with `element_id` and `profile | null`.
- [ ] The UML document sidebar includes a Card titled **Perfil de generación**.
- [ ] Class and attribute targets can be selected from the current document model.
- [ ] Existing class profile values prefill `auditable`, `readOnly`, and `crud` controls.
- [ ] Existing attribute profile values prefill `searchable`, `sortable`, and `readOnly` controls.
- [ ] Submitting declared controls sends `SetGenerationProfile` through the existing REST `submitCommand` flow.
- [ ] Submitting all controls unset sends `profile: null` to clear the profile.
- [ ] Backend 422 details are displayed without unmounting or crashing the panel.
- [ ] No backend, persistence, canvas, WebSocket, Flutter, or `defaultSort` changes are made.
