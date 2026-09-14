# Design: UML Canvas Remove UI

## Technical Approach

Pure frontend. Three new presentational controls under
`components/workspace/`, each taking `onSubmit: (command: UmlCommandIn) =>
Promise<CommandResult>` exactly like `AddAttributeForm` /
`AddRelationshipControl`, plus three new members on the `UmlCommandIn`
union and three JSX lines in `documents/[docId]/page.tsx`. Nothing new
enters `state/document.ts`: `useDocument.submitCommand` already does
POST → `await getDocument` → `setDocument` (prior DD3), so a removal
refreshes the canvas through the identical path an add does. `backend/`
diff is empty.

## Decision Drivers

- The command bus is frozen and its remove payloads are already final in
  `backend/apps/uml_documents/schemas.py`; the frontend union must match
  those field names byte-for-byte.
- `remove_class` cascades relationships silently and `CommandResultOut`
  returns only `{revision, validation}` — the UI can never *report* what
  a removal destroyed, so it must *predict* it before submitting.
- Every remove command is a no-op on an unknown id: a stale `<select>`
  value produces a silent, invisible failure, not an error. This is the
  one real hazard of the cycle.
- The prior cycle's controls keep transient state in `useState` and derive
  everything else from props each render; `react-hooks/set-state-in-effect`
  is enforced (see `state/document.ts`'s render-time reset).

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | Extend `UmlCommandIn` with three members whose fields are copied from the real Pydantic schemas: `{type: "RemoveClass"; class_id: string}`, `{type: "RemoveAttribute"; class_id: string; attribute_id: string}`, `{type: "RemoveRelationship"; relationship_id: string}`. Replace the stale "Only the three command shapes this cycle submits" comment with one naming the six now wired and `RenameClass` as the sole remaining gap | Add all seven shapes now; a generic `{type: string; [k: string]: unknown}` escape hatch | `RemoveAttributeIn` carries **both** `class_id` and `attribute_id` (attribute ids are only unique within a class) and `RemoveRelationshipIn` carries **only** `relationship_id` — asymmetries a guessed shape gets wrong and the 422 `invalid_command_payload` only reports at runtime. `RenameClass` stays out because no UI collects a new name (proposal §Out of Scope) |
| DD2 | **Stale selection is eliminated by derivation, not by an effect.** Each control stores the raw selected id in `useState`, then derives `const selected = options.find(o => o.id === rawId) ?? null` on every render and feeds `value={selected?.id ?? ""}` to the `<select>`. `handleSubmit` early-returns when `selected === null` | `useEffect(() => { if (!options.some(...)) setId("") }, [options])`; keying the control on `document.revision` to remount it | An effect fires *after* a render in which the `<select>` is already holding a dead id, so a fast submit between refetch and effect still posts the stale id — the exact silent no-op this cycle must prevent. Derivation makes the dead id unrepresentable in the same render pass, needs no dependency array over a prop array whose identity changes every refetch, and keeps the component compliant with `react-hooks/set-state-in-effect`. Remount-by-key would also discard the confirmation step mid-flow |
| DD3 | Each `<select>` renders a leading `<option value="">` placeholder, and the submit `Button` is `disabled` when `selected === null` | Preselect `options[0]?.id` as `AddAttributeForm` does | A destructive control must not arrive pre-aimed at a class the user never chose, and the placeholder gives DD2's collapsed-to-`""` state a real option to bind to instead of an out-of-range controlled value. `AddAttributeForm`'s init-only `useState(classes[0]?.id ?? "")` carries the same staleness bug; it is **not** touched this cycle (out of scope) but is recorded as an open question |
| DD4 | `RemoveClassControl` renders its confirmation as a **second in-component render branch** gated by a `confirming` boolean, replacing the select with the warning + `Confirmar`/`Cancelar` buttons — the same early-return-on-state shape `AddRelationshipControl` uses for pending-source vs. pending-target | `window.confirm()`; a modal/`<dialog>` component; an "are you sure" checkbox | `window.confirm` is untestable under RTL/jsdom without stubbing a global, blocks the event loop, and is the one UI primitive this codebase uses nowhere. No modal primitive exists in `components/ui/` today, and introducing one for a single call site is scope the proposal excludes. The branch shape is already proven in this directory and asserts cleanly with `getByText` |
| DD5 | The cascade count is derived at render from the `relationships` prop: `relationships.filter(r => r.source.class_id === selected.id \|\| r.target.class_id === selected.id).length`, recomputed for the confirm branch, never stored in state | Compute once when entering the confirm step; ask the server | Mirrors `remove_class`'s own source-or-target filter (spec pins this) and matches `page.tsx`'s existing `danglingRelationshipCount` derivation. Storing it would let a concurrent refetch leave a confirm dialog quoting a number the model no longer has |
| DD6 | Relationship option label: `` `${name(source.class_id)} → ${name(target.class_id)} (${r.kind})` ``, where `name(id) = classes.find(c => c.id === id)?.name ?? id`. Dangling relationships are **listed, not filtered** | Reuse the canvas edge label (`formatMultiplicity(src) → formatMultiplicity(tgt)`); filter to renderable edges like `toElements` does | Multiplicities do not identify *which* relationship to delete when two classes are linked twice; endpoint names plus kind do. The `?? id` fallback follows `AddRelationshipControl`'s `sourceClass?.name ?? pendingSourceId`. `toElements` drops dangling edges from the canvas, so this control is the **only** way to delete one — filtering here would make them permanently unreachable |
| DD7 | All three controls render in `page.tsx` after the existing `Add*` block, in Class → Attribute → Relationship order, under an `<h2>Eliminar</h2>` heading; `ValidationPanel` stays where it is (above the forms) | Interleave each `Remove*` beside its `Add*`; put them above `ValidationPanel` | Grouping the destructive controls behind one heading keeps a mis-click from landing on a remove select while adding, and leaves the existing add flow's DOM order — which the container test asserts — undisturbed. `ValidationPanel` must stay above so a post-removal diagnostic is visible without scrolling past the forms |
| DD8 | Error handling and submit locking are copied verbatim: `useState` `error`/`submitting`, `catch (err) { err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo." }`, `<p role="alert" className="text-sm text-destructive">`. Buttons use the existing `destructive` variant | A shared `useCommandSubmit` hook extracted from all six controls | The extraction is a real improvement but would rewrite three already-verified components; this cycle stays additive (proposal §Rollback Plan). Logged as tech debt |

## Data Flow

    RemoveClassControl ─┐
    RemoveAttributeControl ─┼─ onSubmit(command) ──→ page.tsx ──→ useDocument.submitCommand
    RemoveRelationshipControl ─┘                                        │
                                                                        │ POST /commands
                                                                        │ await getDocument   (DD3, prior cycle)
                                                                        ▼
              fresh document.model ──→ classes[] / relationships[] props ──→ back into the controls
                       │                                                          │
                       └──→ DiagramCanvas (revision-keyed)                        └──→ DD2 derivation
                                                                                        collapses any
                                                                                        now-missing id to ""

    RemoveClassControl only:
      select class → [Eliminar] → confirming=true → "Se eliminarán también N relación(es)"
                                      → [Confirmar] → onSubmit   |   [Cancelar] → confirming=false

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/lib/uml_documents.ts` | Modify | +3 `UmlCommandIn` members (DD1); replace the stale union comment |
| `frontend/src/components/workspace/RemoveClassControl.tsx` | Create | Class select + confirmation branch with cascade count (DD2/DD4/DD5) |
| `frontend/src/components/workspace/RemoveAttributeControl.tsx` | Create | Class select → attribute select, immediate submit (DD2) |
| `frontend/src/components/workspace/RemoveRelationshipControl.tsx` | Create | Relationship select, immediate submit (DD2/DD6) |
| `frontend/src/app/(app)/documents/[docId]/page.tsx` | Modify | Renders the three controls under an "Eliminar" heading (DD7) |
| `frontend/src/components/workspace/__tests__/Remove*Control.test.tsx` | Create | One RTL suite per control |
| `frontend/src/lib/__tests__/uml_documents.test.ts` | Modify | Type-level coverage of the three new shapes |
| `docs/ai/DECISIONS_LOG.md`, `docs/ai/CURRENT_STATE.md` | Modify | `config.yaml` `rules.design` requires DD1–DD8 be logged there too |
| `backend/**` | **None** | Zero diff — confirmed |

## Interfaces / Contracts

### `lib/uml_documents.ts` — union extension (DD1)

```ts
/**
 * Six of the seven backend command shapes. Only `RenameClass` remains
 * unwired — no UI collects a new name (proposal §Out of Scope).
 * Field names are copied from `apps/uml_documents/schemas.py`.
 */
export type UmlCommandIn =
  | { type: "AddClass"; class_id: string; name: string }
  | { type: "AddAttribute"; class_id: string; attribute: { /* unchanged */ } }
  | { type: "AddRelationship"; relationship: { /* unchanged */ } }
  | { type: "RemoveClass"; class_id: string }
  | { type: "RemoveAttribute"; class_id: string; attribute_id: string }
  | { type: "RemoveRelationship"; relationship_id: string };
```

### Control props

```ts
type RemoveClassControlProps = {
  classes: UmlClass[];
  relationships: Relationship[];          // cascade count source (DD5)
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
};
type RemoveAttributeControlProps = {
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
};
type RemoveRelationshipControlProps = {
  classes: UmlClass[];                    // id → name for the label (DD6)
  relationships: Relationship[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
};
```

### DD2 derivation — the shape every control repeats

```tsx
const [classId, setClassId] = useState("");
const selectedClass = classes.find((c) => c.id === classId) ?? null;   // stale id → null
// RemoveAttributeControl chains off it; options exist only while the parent does:
const attributes = selectedClass?.attributes ?? [];
const [attributeId, setAttributeId] = useState("");
const selectedAttribute = attributes.find((a) => a.id === attributeId) ?? null;

async function handleSubmit(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  if (selectedClass === null || selectedAttribute === null) return;     // never posts a dead id
  ...
  await onSubmit({ type: "RemoveAttribute", class_id: selectedClass.id, attribute_id: selectedAttribute.id });
  setAttributeId("");                                                   // clear-on-success, CreateOrgForm convention
}

<select value={selectedClass?.id ?? ""} onChange={(e) => { setClassId(e.target.value); setAttributeId(""); }}>
  <option value="">Selecciona una clase</option>
  {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
</select>
```

`RemoveClassControl`'s confirm branch is `confirming && selectedClass !== null` — a
class that vanishes mid-confirmation falls back to the select instead of stranding a
dialog over a dead id.

### Confirmation copy (DD4/DD5, Spanish, matching every `workspace/*` string)

```
Se eliminará la clase «{selectedClass.name}».
Se eliminarán también {cascadeCount} relación(es) que la referencian.
[Confirmar eliminación]  [Cancelar]
```

When `cascadeCount === 0` the second line is omitted; the confirmation step itself is
**not** skipped (spec: class removal always confirms).

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit — `lib/uml_documents.ts` | `submitCommand` forwards each new shape verbatim as the JSON body | `vi.mock("@/lib/api")`, extending the existing suite |
| Component — `RemoveClassControl` | Selecting + submitting shows the confirm step and **does not** call `onSubmit`; `Confirmar` calls it once with `{type:"RemoveClass", class_id}`; the count equals the source-or-target filter (fixture: 2 of 3 relationships touch the class); `Cancelar` returns to the select with no call; `cascadeCount === 0` omits the cascade line but still confirms | RTL, `onSubmit: vi.fn().mockResolvedValue(...)`, mirroring `CreateOrgForm.test.tsx` |
| Component — `RemoveAttributeControl` | Attribute options follow the selected class; changing class clears the attribute; submits `{class_id, attribute_id}` with no confirm step | RTL |
| Component — `RemoveRelationshipControl` | Label reads `A → B (association)`; a dangling relationship still appears using its raw `class_id`; submits `{relationship_id}` immediately | RTL |
| Component — stale selection (DD2, all three) | `rerender` with a props array from which the selected id was removed → the `<select>` reads `""`, the submit button is disabled, and a submit attempt makes **zero** `onSubmit` calls | RTL `rerender` with a second fixture, no refetch mock needed |
| Container | `page.tsx` renders the three controls with the fresh `classes`/`relationships` props and `submitCommand` | RTL with `useDocument` mocked (existing container suite) |
| E2E | Deferred — no Cypress harness exists (`config.yaml` `testing.e2e`) | — |

## Threat Matrix

N/A — no routing decisions from untrusted input, shell, subprocess, VCS/PR
automation, executable-file classification, or process integration. Removal ids
originate from the already-loaded, tenant-scoped document and travel through the
existing authenticated `apiFetch` seam.

## Migration / Rollout

No migration, no feature flag, no data change. Additive except two edited files;
rollback is deleting the three components, their JSX, and the three union members
(proposal §Rollback Plan).

## Open Questions

- [ ] `AddAttributeForm`'s `useState(classes[0]?.id ?? "")` has the same staleness
      bug DD2 fixes. Out of scope here — should `sdd-tasks` add a follow-up unit, or
      is it a separate cycle?
- [ ] Six controls now duplicate the `error`/`submitting`/`ApiError` block (DD8).
      Extraction into a `useCommandSubmit` hook is recorded as tech debt for the
      next cycle.
