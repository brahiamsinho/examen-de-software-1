# Proposal: UML Class-Diagram Canvas UI

## Intent

Cycle 3 (`uml-document-persistence`) exposed create/get/submit-command over
HTTP, but no human can reach it: `frontend/src/` has zero diagram UI, and
the already-installed `cytoscape` + `cytoscape-fcose` have zero imports.
This cycle delivers the first end-to-end manual-input use case — a user
opens a document, sees its classes, and edits it through the command bus.

## Scope

### In Scope

- `app/(app)/documents/[docId]/page.tsx` — first dynamic route; loads a
  document (org slug from `activeOrgSlugAtom`, not the URL).
- A "New Diagram" entry point on `(app)/dashboard/page.tsx` (only when an
  active org exists): submits `name`, calls `POST /documents`, and
  navigates to the new document's page. Without this, `/documents/{docId}`
  is unreachable — `dashboard/page.tsx` currently has no document list or
  creation affordance at all.
- Render classes + their attributes as Cytoscape nodes, relationships as
  edges; auto-layout via `fcose` on every load.
- Add class (`add_class`).
- Add attribute — primitive types only, no `enumeration_ref` (`add_attribute`).
- Add relationship — `association` kind only, click-click source→target.
- Non-blocking validation panel showing violations from `CommandResultOut`.
- Refetch full document via `GET` after every accepted command.

### Out of Scope

- Layout persistence / drag-to-reposition (no backend command exists).
- Undo/redo, command history.
- Operations/methods UI (no `add_operation` command exists).
- Enumerations UI and `enumeration_ref` attribute types.
- Relationship edit or removal; relationship kinds beyond `association`.
- Remove-class / remove-attribute UI — commands exist backend-side but
  are deliberately deferred to keep this cycle's diff reviewable.
- Any backend change. `backend/` has zero diff this cycle.

## Capabilities

### New Capabilities

- `web-uml-canvas`: document page, Cytoscape rendering, the three add
  interactions, and non-blocking validation display.

### Modified Capabilities

None. `uml-document-persistence` behavior is consumed, not changed.

## Approach

Follow the `organizations`/`members` layering exactly:

| Layer | File |
|---|---|
| API | `frontend/src/lib/uml_documents.ts` (hand-written TS mirroring the codec) |
| State | `frontend/src/state/document.ts` (`useDocument`: load + `submitCommand` + refetch) |
| View | `frontend/src/components/workspace/{DiagramCanvas,AddClassForm,AddAttributeForm,ValidationPanel}.tsx` |
| Container | `frontend/src/app/(app)/documents/[docId]/page.tsx` |
| Entry point | `frontend/src/components/workspace/CreateDocumentForm.tsx` + a small addition to `frontend/src/app/(app)/dashboard/page.tsx` |

`DiagramCanvas` is a thin `useRef`/`useEffect` Cytoscape wrapper (no
binding library), consistent with the `apiFetch` thin-seam convention.
Auth is inherited from `(app)/layout.tsx`.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Cytoscape mount/update/unmount lifecycle is new ground here | Med | Flag for sdd-design: explicit teardown; re-layout only on revision change |
| Hand-written TS types drift from the backend codec | Med | Flag for sdd-spec: pin types to a real `DocumentOut` fixture |
| Refetch-per-command adds a round-trip and can flicker | Accepted | Confirmed user decision |

## Rollback Plan

Purely additive frontend files plus one new route segment. Revert via
`git revert`, or delete the four new modules and the `documents/` route.

## Dependencies

None new — `cytoscape` ^3.34.2 and `cytoscape-fcose` ^2.2.0 already in
`frontend/package.json`.

## Success Criteria

- [ ] A user can create a new document from the dashboard and land on its
      canvas page.
- [ ] A user can open `/documents/{docId}` and see persisted classes.
- [ ] Add class / attribute / association each submit one command and the
      canvas reflects the refetched document.
- [ ] Violations render in a panel without blocking further edits.
- [ ] `backend/` diff is empty.
- [ ] Vitest + RTL cover the new state hook and forms.
