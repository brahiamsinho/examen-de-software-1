# Exploration: UML class-diagram canvas UI (frontend)

## Current State

- Next.js 16.3.3 App Router, React 19.2.8, Jotai. Route groups `(auth)`/`(gate)`/`(app)`; no dynamic `[param]` segment exists anywhere yet in this app.
- **Org scoping is atom-based, not URL-based**: `activeOrgSlugAtom` (`frontend/src/state/organizations.ts`) supplies `orgSlug` to every API call; pages never encode it in the route. A new document page would be `app/(app)/documents/[docId]/page.tsx` — the first dynamic route in the app — reading org slug from the atom.
- Layered convention (from `organizations`/`members`): `lib/{domain}.ts` (typed `apiFetch` wrappers) → `state/{domain}.ts` (Jotai atom+hook for shared state, or local `useState` for single-consumer resettable state, per `useMembers`) → `components/workspace/*.tsx` (presentational, props-in/callback-out) → `app/(app)/.../page.tsx` (container). All HTTP goes through the single `apiFetch` seam in `frontend/src/lib/api.ts` (CSRF handling, `ApiError`/`NetworkError`). `(app)/layout.tsx` already server-guards auth (`requireUser`) + client `<SessionGuard>` — a new canvas route inherits this for free.
- Backend contract (frozen, read for shape only): `backend/apps/uml_documents/api.py` (3 endpoints), `schemas.py` (`CommandIn` 7-member discriminated union), `services.py`. `DocumentOut.model`/`.layout` are raw `dict` — no schema codegen exists, so TS types must be hand-written to mirror the codec output. `CommandResultOut` returns only `{revision, validation}`, **not** the updated model.

## Affected Areas

- `frontend/src/lib/uml_documents.ts` (new) — typed API wrappers for the 3 endpoints.
- `frontend/src/state/document.ts` (new) — load + `submitCommand` hook, mirroring `useMembers`.
- `frontend/src/components/workspace/DiagramCanvas.tsx` (new) — Cytoscape mount wrapper.
- `frontend/src/components/workspace/{AddClassForm,AddAttributeForm,ValidationPanel}.tsx` (new) — presentational.
- `frontend/src/app/(app)/documents/[docId]/page.tsx` (new) — first dynamic route, container.
- No backend files affected.

## Approaches — diagramming library

This is **not an open decision**: `openspec/config.yaml`'s context already commits to Cytoscape.js, and `frontend/package.json` already has `cytoscape ^3.34.2` + `cytoscape-fcose ^2.2.0` installed — but zero imports exist anywhere in `frontend/src` (confirmed via grep). This cycle is the first real usage.

1. **Use installed Cytoscape.js + cytoscape-fcose directly** (thin custom `useRef`/`useEffect` wrapper, no binding library like `react-cytoscapejs` is installed) — Pros: honors the already-paid-for stack decision, zero new dependency, `fcose` gives free auto-layout for a first cycle with no persisted positions. Cons: no React-idiomatic binding, must hand-roll mount/update/unmount lifecycle.
   - Effort: Low
2. **React Flow / xyflow** — Pros: React-native API, less imperative glue code. Cons: contradicts a settled stack decision, adds a new dependency for no real gain given Cytoscape is already installed and paid for.
   - Effort: Medium (mostly the cost of relitigating + swapping deps)
3. **Konva (canvas-based, not SVG/DOM)** — Pros: fine for freeform drawing. Cons: worse fit for structured graph editing (no built-in graph model, edges, or layout algorithms) — would need to reimplement what Cytoscape already provides.
   - Effort: High

## Recommendation

Use the already-installed Cytoscape.js + cytoscape-fcose via a small custom wrapper component, consistent with the existing "thin custom seam, no extra abstraction library" convention (`apiFetch`). Scope the first cycle to: create document → render classes/attributes read-only → add class → add attribute (primitive types only) → add relationship (association only) → display validation violations inline. Defer layout persistence, undo/redo, operations, enumerations UI, and relationship edit/remove — several of these (layout persistence, operations) are not just "deferred by choice" but currently **unbuildable** without new backend commands, since `CommandIn`'s union has no `UpdateLayout` or `AddOperation` member.

## Risks

- `CommandResultOut` returns only `{revision, validation}`, never the updated `model` — every command submission will need either an optimistic local mutation (duplicating server logic client-side) or a forced refetch of the whole document; this needs a user decision, not a silent one.
- Layout positions have no corresponding command at all — persisting drag-to-reposition in this cycle would require backend work, not just frontend work, contradicting the framing of this as a pure frontend cycle.
- No relationship-drawing interaction precedent exists in this codebase (click-click vs. drag) — picking one silently would bake in UX the user hasn't confirmed.
- No React-Cytoscape binding library is installed; the wrapper component's mount/update/unmount lifecycle is new, untested ground for this codebase.

## Open Questions (for the user, before proposal)

1. Relationship interaction model: click-click (select source class, then target class) vs. drag-to-connect (needs an additional Cytoscape extension, e.g. `cytoscape-edgehandles`).
2. Layout persistence: stays client-side/ephemeral this cycle (no backend command exists for it) vs. adding a new backend command to persist positions — the latter would expand this cycle beyond pure frontend.
3. Command-application strategy: optimistic client-side mutation after each command (duplicates server logic) vs. refetch the whole document after every command (simpler, extra round-trip).
4. Validation UX: block further edits when the API returns a blocking violation vs. always allow further edits and just display violations non-blockingly (mirrors the backend's own Always-Apply Diagnostics Policy).

## Scope Decisions (confirmed by user)

1. Relationship interaction model: **click-click** (select source class, then target class). No new Cytoscape extension needed.
2. Layout persistence: **client-side/ephemeral only** this cycle. Auto-layout via `cytoscape-fcose` on every load; no backend command for positions is added.
3. Command-application strategy: **refetch the whole document** (GET) after every submitted command, rather than optimistic client-side mutation.
4. Validation UX: **non-blocking display** — violations render in a panel, editing stays available, mirroring the backend's Always-Apply Diagnostics Policy.

## Ready for Proposal

Yes — all open questions resolved above.
