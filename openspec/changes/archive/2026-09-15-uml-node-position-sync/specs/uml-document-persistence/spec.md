# Delta for UML Document Persistence

## ADDED Requirements

### Requirement: Layout Persistence via Non-Command Path

The system MUST provide a service function, sibling to `submit_command`,
that persists a `DiagramLayout` update by calling
`ProjectDocument.with_layout()` under the same `@transaction.atomic` +
`select_for_update()` guarantee already used for command persistence, then
broadcasts the result via `broadcast_document`. This path MUST NOT route
through `dispatcher.apply()` or any `UmlCommand` variant, and the
`UmlCommand` union and its dispatcher MUST remain unmodified as a result of
this path's existence.

#### Scenario: Layout write persists and broadcasts without a command

- GIVEN an existing document at revision N
- WHEN the layout-write service function is called with a new final
  position for a class
- THEN the resulting `UmlDocument.layout` is persisted and the updated
  document is broadcast to the document's group, with no `UmlCommand`
  submitted

#### Scenario: UmlCommand union has zero diff

- GIVEN this change's complete diff
- WHEN the `UmlCommand` union and its dispatcher are inspected
- THEN neither shows any modified, added, or removed variant or dispatch
  branch

### Requirement: Revision Bumps Only on Persisted Position Release

`UmlDocument.revision` MUST increment by exactly 1 when a position release
is persisted via the layout write path, and MUST NOT increment for a claim
or for any `position_update`, since neither reaches this persistence path.

#### Scenario: Release increments revision by exactly 1

- GIVEN a document at revision N
- WHEN a position release is persisted via the layout write path
- THEN the document's revision becomes exactly N + 1

#### Scenario: Live position updates never touch revision

- GIVEN a document at revision N
- WHEN any number of `position_update` messages are processed for that
  document without a release
- THEN the document's revision remains N

### Requirement: Absent Class Ids Are Pruned From Persisted Layout

When persisting a layout update, an entry referencing a class id no longer
present in the document's current `CanonicalUmlModel` MUST be dropped
rather than persisted or causing an error.

#### Scenario: Persisting a position for a since-removed class is a no-op

- GIVEN a class was removed from the document after a drag on it began
- WHEN the layout-write service function is called with that now-absent
  class id
- THEN the entry is dropped without error and the persisted layout contains
  no entry for that class id
