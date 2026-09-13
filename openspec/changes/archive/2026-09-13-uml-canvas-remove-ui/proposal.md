# Proposal: UML Canvas Remove UI

## Intent

The previous cycle (`uml-canvas-ui`) deliberately deferred removal to keep
its diff reviewable, so a diagram can only grow: a user who adds a wrong
class, attribute, or relationship must recreate the document. The backend
already accepts `RemoveClass`, `RemoveAttribute`, and `RemoveRelationship`
through the same command bus — only the frontend is missing. This cycle
closes the create/destroy gap with no backend diff.

## Scope

### In Scope

- Extend `UmlCommandIn` with the three remove shapes and replace its stale
  "only three commands" comment.
- `RemoveClassControl` — class `<select>` plus a confirmation step that
  states how many relationships will cascade away, counted client-side
  from `document.model.relationships`.
- `RemoveAttributeControl` — class `<select>` + attribute `<select>`,
  removes immediately on submit.
- `RemoveRelationshipControl` — relationship `<select>` labelled from the
  existing edge-label helpers, removes immediately on submit.
- Wire all three into `documents/[docId]/page.tsx`, reusing `submitCommand`
  and the existing refetch-after-command path.

### Out of Scope

- Any backend change. `backend/` diff is empty — all three commands,
  their schemas, and their cascade behavior already exist and are tested.
- Bulk or multi-select removal.
- Undo of a removal; command history.
- Canvas-gesture removal (right-click, remove-mode toggle) — rejected in
  exploration because attributes are baked into node labels (DD7) and have
  no tap target.
- Removal of enumerations or operations (no UI exists for either).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-uml-canvas`: adds remove-class / remove-attribute /
  remove-relationship interactions, plus the cascade confirmation
  requirement for class removal.

## Approach

Reuse the established layering verbatim: presentational components under
`components/workspace/` taking an `onSubmit: (command) => Promise<CommandResult>`
prop, state and wiring in the container page. Naming follows the existing
split — `*Control` (selection only, no free-text input) rather than
`*Form`, matching `AddRelationshipControl`.

The cascade count is derived, not stored: `relationships.filter(r => r.source.class_id === id || r.target.class_id === id).length`,
the same client-side derivation `danglingRelationshipCount` already uses.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/src/lib/uml_documents.ts` | Modified | 3 command shapes added to `UmlCommandIn` |
| `frontend/src/components/workspace/Remove{Class,Attribute,Relationship}Control.tsx` | New | 3 presentational controls |
| `frontend/src/app/(app)/documents/[docId]/page.tsx` | Modified | Renders the 3 controls |
| `backend/` | None | Already wired |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Cascade count drifts from server behavior (client-derived) | Med | Flag for sdd-spec: pin the count rule to `remove_class`'s source/target filter |
| Stale `<select>` value after a removal refetch | Med | Flag for sdd-design: reset selection when the selected id disappears |
| Removing an unknown id is a silent backend no-op | Low | Selects only offer ids from the loaded document |

## Rollback Plan

Additive except two edited files. Revert via `git revert`, or delete the
three new components and drop their JSX plus the three union members.

## Dependencies

None new.

## Success Criteria

- [ ] A user can remove a class, an attribute, and a relationship from
      `/documents/{docId}`, and the refetched canvas reflects each one.
- [ ] Removing a class with relationships shows the exact cascade count
      and does not submit until confirmed.
- [ ] Removing an attribute or a relationship submits with no confirmation.
- [ ] `backend/` diff is empty.
- [ ] Vitest + RTL cover the three new controls, including the
      confirmation path and its cascade count.
