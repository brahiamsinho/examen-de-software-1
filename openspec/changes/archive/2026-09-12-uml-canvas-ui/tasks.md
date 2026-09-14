# Tasks: UML Class-Diagram Canvas UI

Strict TDD. Test command: `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/state/__tests__/document.test.ts src/components/workspace/__tests__/DiagramCanvas.test.tsx src/components/workspace/__tests__/AddClassForm.test.tsx src/components/workspace/__tests__/AddAttributeForm.test.tsx src/components/workspace/__tests__/AddRelationshipControl.test.tsx src/components/workspace/__tests__/ValidationPanel.test.tsx src/components/workspace/__tests__/CreateDocumentForm.test.tsx "src/app/(app)/documents/[docId]/__tests__/page.test.tsx" "src/app/(app)/dashboard/__tests__/page.test.tsx"`.
Full-suite regression: `cd frontend && npm test`. Frontend-only; `backend/` stays untouched.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1250-1350 (production: `uml_documents.ts` ~180, `document.ts` ~55, `DiagramCanvas.tsx` ~100, `AddClassForm.tsx` ~35, `AddAttributeForm.tsx` ~55, `AddRelationshipControl.tsx` ~70, `ValidationPanel.tsx` ~30, `CreateDocumentForm.tsx` ~35, `documents/[docId]/page.tsx` ~90, `dashboard/page.tsx` diff ~20; tests: ~90+90+120+35+50+60+30+35+90+30) |
| 800-line budget risk | **High** — exceeds the session's single-pr/800-line budget |
| Chained PRs recommended | **Yes** |
| Suggested split | PR 1 (data layer + canvas) -> PR 2 (forms) -> PR 3 (container wiring + verification) |
| Delivery strategy | single-pr (per session context) |
| Chain strategy | `size:exception` — accepted by user |

Decision needed before apply: Resolved
Chain strategy: size:exception
800-line budget risk: High (accepted)

Delivery strategy for this session is `single-pr`. The user explicitly accepted
`size:exception` for this cycle: the 3 suggested work units are tightly coupled
(data -> canvas -> forms -> wiring) and an intermediate PR boundary would not be an
independently usable feature, mirroring the precedent set in `uml-document-persistence`.
Proceeding with `sdd-apply` as a single PR.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `lib/uml_documents.ts` types/wrappers, `state/document.ts`, `DiagramCanvas.tsx` (incl. `toElements`) | PR 1 | `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/state/__tests__/document.test.ts src/components/workspace/__tests__/DiagramCanvas.test.tsx` | N/A — pure unit/mocked tests; jsdom has no canvas, no live harness needed | Delete the 3 new files and their tests — no route or dashboard change depends on them yet |
| 2 | `AddClassForm`, `AddAttributeForm`, `AddRelationshipControl`, `ValidationPanel`, `CreateDocumentForm` | PR 2 | `cd frontend && npx vitest run src/components/workspace/__tests__/{AddClassForm,AddAttributeForm,AddRelationshipControl,ValidationPanel,CreateDocumentForm}.test.tsx` | N/A — presentational components tested via RTL, no route wiring yet | Delete the 5 new component/test file pairs; PR 1's canvas/state stay independently valid |
| 3 | `documents/[docId]/page.tsx`, `dashboard/page.tsx` modification, integration | PR 3 | `cd frontend && npm test` | `cd frontend && npm run dev` + manual create-document -> open-canvas -> add-class round trip | Revert `page.tsx`, the new route folder, and the `dashboard/page.tsx` diff — PR 1/2 remain functional as a library |

## Phase 1: Data Layer (`lib/uml_documents.ts`)

- [x] 1.1 RED: `frontend/src/lib/__tests__/uml_documents.test.ts` — pin the wire
  fixture from design.md; `createDocument`/`getDocument`/`submitCommand` call
  the right path/method/body via mocked `apiFetch`; `ApiError` propagates
  unmodified; `formatMultiplicity` covers `1`/`0..1`/`0..*`;
  `attributeTypeLabel` covers both `PrimitiveType` and `EnumerationRef`.
- [x] 1.2 GREEN: create `frontend/src/lib/uml_documents.ts` — all types
  (`UmlModel`, `UmlClass`, `UmlAttribute`, `Relationship`, `Multiplicity`,
  `UmlDocument`, `Diagnostic`, `CommandResult`, `UmlCommandIn`), `PRIMITIVE_TYPES`,
  the 3 `apiFetch` wrappers, `formatMultiplicity`, `attributeTypeLabel`.
  [Diagram Rendering data shape; Add Attribute Command primitive-only types; DD1, DD10, DD12]

## Phase 2: State (`state/document.ts`)

- [x] 2.1 RED: `frontend/src/state/__tests__/document.test.ts` — `useDocument`
  loads on mount when `orgSlug !== null`; resets `document`/`loading`/
  `lastValidation` when `docId` changes; `submitCommand` calls POST then GET
  in that order and stores `result.validation`; a rejected POST leaves
  `document` untouched and rethrows.
- [x] 2.2 GREEN: create `frontend/src/state/document.ts` — `useDocument(orgSlug,
  docId)` per design's Interfaces/Contracts block. [Add Class/Attribute/
  Relationship Command refetch; Graceful Handling of Malformed Command
  Responses; DD2, DD3]

## Phase 3: Diagram Canvas (`DiagramCanvas.tsx`)

- [x] 3.1 RED: `frontend/src/components/workspace/__tests__/DiagramCanvas.test.tsx`
  (pure section, no DOM) — `toElements` on the pinned fixture produces the
  expected nodes (label includes attribute lines) and edges (multiplicity
  label via `formatMultiplicity`); an edge whose endpoint class is missing
  from `model.classes` is dropped.
- [x] 3.2 RED: same file, Cytoscape-mocked section — `vi.mock("cytoscape")`
  returning a fake `Core`; constructs once on mount, `destroy()` on unmount,
  `cy.json`+`cy.layout({name:"fcose"})` called on `revision` change and NOT
  on an unrelated re-render; `tap` handler routes through `onNodeTapRef` to
  the latest `onNodeTap`; `highlightedClassId` toggles the `selected-source`
  class without re-running layout.
- [x] 3.3 GREEN: create `frontend/src/components/workspace/DiagramCanvas.tsx`
  — `cytoscape.use(fcose)` at module scope, exported pure `toElements`, mount
  effect, revision-keyed update effect, highlight-only effect, per design's
  DD4-DD9. [Diagram Rendering — nodes/edges/auto-layout scenarios]

## Phase 4: Forms

- [x] 4.1 RED: `frontend/src/components/workspace/__tests__/AddClassForm.test.tsx`
  — submitting a name calls `onSubmit` with an `AddClass` command shape and
  clears the input on success.
- [x] 4.2 GREEN: create `frontend/src/components/workspace/AddClassForm.tsx`.
  [Add Class Command]
- [x] 4.3 RED: `frontend/src/components/workspace/__tests__/AddAttributeForm.test.tsx`
  — class select + name + type select renders only the 8 `PRIMITIVE_TYPES`
  (no enumeration option); submitting calls `onSubmit` with an `AddAttribute`
  command for the selected class and clears on success.
- [x] 4.4 GREEN: create `frontend/src/components/workspace/AddAttributeForm.tsx`.
  [Add Attribute Command; Enumeration types are not offered]
- [x] 4.5 RED: `frontend/src/components/workspace/__tests__/AddRelationshipControl.test.tsx`
  — renders the pending-source prompt when `pendingSourceId` is set; renders
  both multiplicity selects when both ids are set; `onSubmit` builds an
  `association` `AddRelationship` command with a generated id and clears both
  ids on success.
- [x] 4.6 GREEN: create `frontend/src/components/workspace/AddRelationshipControl.tsx`.
  [Add Relationship Command — click-click creates an association; DD10, DD12]
- [x] 4.7 RED: `frontend/src/components/workspace/__tests__/ValidationPanel.test.tsx`
  — renders every `Diagnostic` field (severity, code, message, path) for both
  severities; renders nothing when `lastValidation` is `null`; never disables
  a form via any prop it exposes.
- [x] 4.8 GREEN: create `frontend/src/components/workspace/ValidationPanel.tsx`.
  [Non-Blocking Validation Panel; DD13]
- [x] 4.9 RED: `frontend/src/components/workspace/__tests__/CreateDocumentForm.test.tsx`
  — submitting a name calls `onCreate({name})`; the form does not call
  `useRouter` itself.
- [x] 4.10 GREEN: create `frontend/src/components/workspace/CreateDocumentForm.tsx`.
  [Create-Document Entry Point; DD14]

## Phase 5: Container Wiring

- [x] 5.1 RED: `frontend/src/app/(app)/documents/[docId]/__tests__/page.test.tsx`
  (with `useDocument` mocked) — renders classes/relationships count from
  `document.model`; renders a not-found state on `error` instead of a crash;
  click-click state machine: tap class A sets pending source, tap A again
  cancels, tap A then tap B opens `AddRelationshipControl`.
- [x] 5.2 GREEN: create `frontend/src/app/(app)/documents/[docId]/page.tsx`
  — `"use client"`, `use(params)` per DD11, `useAtomValue(activeOrgSlugAtom)`,
  wires `useDocument`, `DiagramCanvas`, the 3 add-forms, `ValidationPanel`,
  and the click-click handler from DD8/DD9. [Document Page Load — both
  scenarios; DD11]
- [x] 5.3 RED: extend `frontend/src/app/(app)/dashboard/__tests__/page.test.tsx`
  — "New Diagram" entry point is hidden with no active organization; with an
  active organization, submitting a name calls `createDocument` and navigates
  to `/documents/{doc.id}`.
- [x] 5.4 GREEN: modify `frontend/src/app/(app)/dashboard/page.tsx` — render
  `<CreateDocumentForm>` guarded by `activeOrg`, handler calls
  `createDocument` then `router.push`. [Create-Document Entry Point — both
  scenarios]

## Phase 6: Verification

- [x] 6.1 Run `cd frontend && npm test`; confirm all 8 requirements' scenarios
  pass and zero regressions in existing `lib`/`state`/`components/workspace`
  suites.
- [x] 6.2 Run `cd frontend && npm run lint`; confirm zero new warnings.
- [x] 6.3 Confirm `backend/` has zero diff: `git diff --stat backend` returns
  empty.

## Phase 7: Post-Verify Remediation (verify-report.md FAIL — 2 CRITICAL, 3 WARNING)

- [x] 7.1 RED/GREEN: `documents/[docId]/page.tsx` `handleNodeTap` — the
  cancel branch (re-tapping `pendingSourceId`) now also clears
  `pendingTargetId`, so a later fresh-source tap never pre-fills a stale
  target. Regression test in `page.test.tsx` covers tap-A/tap-B/tap-A/tap-C.
  [CRITICAL 1]
- [x] 7.2 RED/GREEN: `state/document.ts` `submitCommand` — validates the
  resolved POST body's shape (`isValidCommandResult`) before writing any
  state; throws a descriptive `Error` on a malformed response instead of
  crashing `ValidationPanel`. Regression test in `document.test.ts`.
  [CRITICAL 2]
- [x] 7.3 RED/GREEN: `state/document.ts` `submitCommand` — wraps the
  post-POST GET in its own try/catch; on GET failure still calls
  `setLastValidation(result.validation)` before surfacing a distinct error.
  Regression test in `document.test.ts`. [WARNING 1]
- [x] 7.4 RED/GREEN: `state/document.ts` `useDocument` now stores a
  `DocumentError = {message, notFound}` instead of a bare string;
  `documents/[docId]/page.tsx` renders "Documento no encontrado" only when
  `notFound` is true, and a distinct generic message otherwise. Regression
  tests in `document.test.ts` and `page.test.tsx`. [WARNING 2]
- [x] 7.5 RED/GREEN: `documents/[docId]/page.tsx` computes a durable
  dangling-relationship count directly from `document.model` (independent of
  `lastValidation`'s lifecycle) and renders a non-blocking note when it is
  `> 0`. Regression tests in `page.test.tsx`. [WARNING 3]
- [x] 7.6 Run `cd frontend && npm test` (212/212 passed) and
  `cd frontend && npm run lint` (zero warnings); confirm `git diff --stat --
  backend` stays empty.
