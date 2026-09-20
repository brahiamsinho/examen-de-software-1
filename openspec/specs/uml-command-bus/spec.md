# UML Command Bus Specification

## Purpose

Give `uml_modeling` a structured, auditable mutation contract. `UmlCommand`
objects plus a thin dispatcher (`apply(document, command) -> CommandResult`)
replace hand-built `CanonicalUmlModel` reconstruction with named, testable
operations, reusing `ProjectDocument.with_model` and `validate(model,
rules=RULES)` — no persistence, no undo/redo, no API in this cycle.

## Requirements

### Requirement: Dispatcher Apply Contract

`apply(document, command)` MUST always return a `CommandResult` carrying a
new `ProjectDocument` (via `document.with_model(...)`) and the
`ValidationResult` of `validate(new_model, rules=RULES)`. It MUST NOT mutate
the input document or its model.

#### Scenario: Original document is untouched
- GIVEN a `ProjectDocument` at revision N
- WHEN any command is applied
- THEN the original document object and its model instance are unchanged
- AND the returned `CommandResult.document.revision` is N + 1

#### Scenario: Validation always runs
- GIVEN any command applied to any document
- WHEN `apply()` returns
- THEN `CommandResult.validation_result` equals `validate(new_model, rules=RULES)`, never `None` or skipped

### Requirement: AddClass

Applying `AddClass` MUST append a new `UmlClass` (given id, name) to
`model.classes`.

#### Scenario: Class is appended
- GIVEN a model with N classes
- WHEN `AddClass` is applied with a new id and name
- THEN the resulting model's `classes` tuple has N + 1 entries, ending with a `UmlClass` matching that id and name

### Requirement: RemoveClass with Cascade

Applying `RemoveClass` MUST remove the matching `UmlClass` from
`model.classes` and MUST cascade-remove every `Relationship` whose `source`
or `target` `class_id` references the removed class, so no dangling
endpoint remains. It MUST also prune `model.generation_metadata` through the
shared `prune_generation_metadata` primitive (DD158), with `removed_ids` equal
to `{class_id}` plus the id of every attribute of the removed class: the entry
keyed by the class id and each entry keyed by one of its attribute ids MUST be
removed, and any *other* entry whose `profile.defaultSort.attribute` is one of
those removed attribute ids MUST have its `defaultSort` cleared (an inheritance
root's `defaultSort` may legitimately point at a descendant's attribute,
DD157). Entries keyed by relationship ids or operation ids MUST be left
untouched (DD159). When the target class is absent the handler MUST remain a
no-op (Missing-Target No-Op Policy). Removing a class that has no metadata
entries MUST leave `generation_metadata` the same object.
(Previously: `RemoveClass` only removed the class and its referencing
relationships and left `generation_metadata` entries for the class and its
attributes behind.)

#### Scenario: Class is removed

- GIVEN a model containing class C among others
- WHEN `RemoveClass(C.id)` is applied
- THEN the resulting model's `classes` no longer contains C
- AND all other classes, enumerations, and relationships are unchanged

#### Scenario: Referencing relationships are cascade-removed

- GIVEN classes A and B and a `Relationship` R with `source.class_id == A.id`
- WHEN `RemoveClass(A.id)` is applied
- THEN the resulting model's `classes` no longer contains A
- AND the resulting model's `relationships` no longer contains R
- AND `validate()` on the result reports no `INVALID_RELATIONSHIP_ENDPOINT` for R

#### Scenario: The class entry and its attribute entries are pruned

- GIVEN class C owning attributes A1 and A2, and `generation_metadata` entries keyed by `C.id`, `A1.id`, `A2.id`, and an unrelated class D
- WHEN `RemoveClass(C.id)` is applied
- THEN the resulting `generation_metadata` contains only the entry for D **[pytest]**

#### Scenario: A root's defaultSort on a removed descendant attribute is cleared

- GIVEN root class R and descendant class S (a `GENERALIZATION` from S to R) owning attribute SA, and `generation_metadata[R.id] == {"profile": {"auditable": true, "defaultSort": {"attribute": SA.id, "direction": "asc"}}}`
- WHEN `RemoveClass(S.id)` is applied
- THEN `generation_metadata[R.id] == {"profile": {"auditable": true}}`, so no `defaultSort` dangles **[pytest]**

#### Scenario: Relationship- and operation-keyed entries are not pruned

- GIVEN `generation_metadata` entries keyed by a relationship id and an operation id of class C
- WHEN `RemoveClass(C.id)` is applied
- THEN those two entries remain in the resulting `generation_metadata` byte-identical **[pytest]**

#### Scenario: Removing a class without metadata leaves generation_metadata untouched

- GIVEN a model whose `generation_metadata` has no entry keyed by C or its attributes and no `defaultSort` referencing them
- WHEN `RemoveClass(C.id)` is applied
- THEN the resulting model's `generation_metadata` is the same object as the input's **[pytest]**

### Requirement: RenameClass

Applying `RenameClass` MUST produce a `UmlClass` with the same `id`,
`attributes`, `operations`, and `visibility`, but with `name` updated.

#### Scenario: Name changes, identity preserved
- GIVEN class C with attributes and operations
- WHEN `RenameClass(C.id, new_name)` is applied
- THEN the resulting class has `id == C.id` and `name == new_name`
- AND its `attributes`/`operations`/`visibility` are unchanged

### Requirement: AddAttribute

Applying `AddAttribute` MUST append a new `UmlAttribute` to the target
class's `attributes` tuple, preserving existing attributes and their order.

#### Scenario: Attribute is appended
- GIVEN class C with existing attributes
- WHEN `AddAttribute(C.id, new_attribute)` is applied
- THEN C's resulting `attributes` tuple equals the original tuple plus `new_attribute` appended

### Requirement: RemoveAttribute

Applying `RemoveAttribute` MUST remove the matching `UmlAttribute` from the
target class's `attributes` tuple, preserving the relative order of the rest.
It MUST also prune `model.generation_metadata` through the shared
`prune_generation_metadata` primitive (DD158) with `removed_ids ==
{attribute_id}`: the entry keyed by the attribute id MUST be removed, and any
entry whose `profile.defaultSort.attribute` equals the removed attribute id
MUST have its `defaultSort` cleared, so no `defaultSort` dangles. Entries keyed
by relationship ids or operation ids MUST be left untouched (DD159). When the
target class or attribute is absent the handler MUST remain a no-op
(Missing-Target No-Op Policy).
(Previously: `RemoveAttribute` only removed the attribute and left its
`generation_metadata` entry, and any `defaultSort` pointing at it, behind.)

#### Scenario: Attribute is removed

- GIVEN class C with attributes including Attr
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN C's resulting `attributes` no longer contains Attr
- AND the remaining attributes keep their original relative order

#### Scenario: The attribute's metadata entry is pruned

- GIVEN class C with attribute Attr and `generation_metadata` entries keyed by `Attr.id` and by another attribute of C
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN the resulting `generation_metadata` has no entry for `Attr.id` and still has the other attribute's entry **[pytest]**

#### Scenario: The owning class's defaultSort pointing at the attribute is cleared

- GIVEN `generation_metadata[C.id] == {"profile": {"crud": ["read"], "defaultSort": {"attribute": Attr.id, "direction": "desc"}}}`
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN `generation_metadata[C.id] == {"profile": {"crud": ["read"]}}` **[pytest]**

#### Scenario: Unrelated entries are untouched

- GIVEN `generation_metadata` entries for class D and for an unrelated attribute, plus a `defaultSort` pointing at a different attribute
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN those entries are byte-identical in the resulting model **[pytest]**

#### Scenario: Removing an attribute without metadata leaves generation_metadata untouched

- GIVEN a model whose `generation_metadata` is empty
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN the resulting model's `generation_metadata` is the same object as the input's **[pytest]**
### Requirement: AddRelationship

Applying `AddRelationship` MUST append a new `Relationship` to
`model.relationships`.

#### Scenario: Relationship is appended
- GIVEN classes A and B in the model
- WHEN `AddRelationship` is applied with source A, target B
- THEN the resulting model's `relationships` tuple contains the new `Relationship`, referencing A and B

### Requirement: RemoveRelationship

Applying `RemoveRelationship` MUST remove the matching `Relationship` from
`model.relationships`, preserving all others.

#### Scenario: Relationship is removed
- GIVEN a model containing relationship R among others
- WHEN `RemoveRelationship(R.id)` is applied
- THEN the resulting model's `relationships` no longer contains R
- AND all other relationships are unchanged

### Requirement: Always-Apply Diagnostics Policy

The dispatcher MUST NOT raise an exception or refuse to apply a command
because the resulting model is invalid. Any such issue MUST surface only as
non-empty diagnostics in `CommandResult.validation_result`.

#### Scenario: Invalid result still applies with diagnostics
- GIVEN a model with only class A
- WHEN `AddRelationship` is applied with source A and a nonexistent target class id
- THEN `apply()` returns a `CommandResult` whose document contains the new relationship
- AND `validation_result.diagnostics` is non-empty and includes an `INVALID_RELATIONSHIP_ENDPOINT` diagnostic
- AND no exception is raised

### Requirement: Missing-Target No-Op Policy

`RemoveClass`, `RemoveAttribute`, `RemoveRelationship`, `AddAttribute`,
`RemoveOperation`, and `AddOperation` targeting an id absent from the model
MUST NOT raise an exception. Each MUST apply as a no-op — the resulting
model's content is identical to the input — mirroring
`CanonicalUmlModel.class_by_id`'s existing None-returning (never raising)
convention for missing lookups. The dispatcher still returns a
`CommandResult` with a new `ProjectDocument` (revision incremented via
`with_model`) and the `ValidationResult` of the unchanged model.
(Previously: this policy covered only `RemoveClass`, `RemoveAttribute`,
`RemoveRelationship`, and `AddAttribute`; it now also covers
`AddOperation`/`RemoveOperation` targeting an unknown class or operation id.)

#### Scenario: Removing an unknown class id is a no-op
- GIVEN a model with no class matching id X
- WHEN `RemoveClass(X)` is applied
- THEN the resulting model's classes, enumerations, and relationships are unchanged in content
- AND the resulting document's revision is exactly one greater than the input's
- AND no exception is raised

#### Scenario: Adding an operation to an unknown class id is a no-op
- GIVEN a model with no class matching id X
- WHEN `AddOperation(X, new_operation)` is applied
- THEN the resulting model's classes are unchanged in content
- AND the resulting document's revision is exactly one greater than the input's
- AND no exception is raised

#### Scenario: Removing an unknown operation id is a no-op
- GIVEN class C with no operation matching id Y
- WHEN `RemoveOperation(C.id, Y)` is applied
- THEN C's resulting `operations` is unchanged in content
- AND no exception is raised
### Requirement: uml_commands Import Boundary

`apps/uml_commands` MUST import only from `apps.uml_modeling` and the Python
standard library. It MUST NOT import Django, `apps.organizations`,
`apps.users`, or any other app.

#### Scenario: No disallowed imports exist
- GIVEN the `uml_commands` package source
- WHEN its imports are statically inspected (an import-boundary test, e.g. AST-based, analogous to `uml_modeling`'s own structural `test_apps.py`)
- THEN every non-stdlib import target is `apps.uml_modeling` or a submodule of it
- AND no import of `django.*`, `apps.organizations`, or `apps.users` is found
### Requirement: AddOperation

Applying `AddOperation` MUST append a new `UmlOperation` to the target
class's `operations` tuple, preserving existing operations and their order.
The operation MUST carry a name, a nullable `return_type`, a visibility, and
an empty `parameters` tuple (`()`); v1 exposes no UI-reachable parameters.

#### Scenario: Operation is appended
- GIVEN class C with existing operations
- WHEN `AddOperation(C.id, new_operation)` is applied
- THEN C's resulting `operations` tuple equals the original tuple plus `new_operation` appended
- AND `new_operation.parameters` is an empty tuple

#### Scenario: Operation with no return type is accepted
- GIVEN class C
- WHEN `AddOperation(C.id, operation)` is applied with `operation.return_type = None`
- THEN C's resulting `operations` tuple contains the operation with `return_type` equal to `None`

### Requirement: RemoveOperation

Applying `RemoveOperation` MUST remove the matching `UmlOperation` from the
target class's `operations` tuple, preserving the relative order of the
rest.

#### Scenario: Operation is removed
- GIVEN class C with operations including Op
- WHEN `RemoveOperation(C.id, Op.id)` is applied
- THEN C's resulting `operations` no longer contains Op
- AND the remaining operations keep their original relative order

### Requirement: SetGenerationProfile

`apps.uml_commands.commands` MUST define a frozen dataclass `SetGenerationProfile(element_id: ElementId, profile: Mapping[str, object] | None = None)` and MUST add it as the LAST member of the `UmlCommand` union. `profile` carries the raw JSON-native mapping as received (DD152); the command module MUST NOT import `apps.relational_mapping`. The dispatcher MUST register `SetGenerationProfile` in `_HANDLERS` to `apps.uml_commands.handlers.generation_profile.set_generation_profile`, so `apply()` returns a `CommandResult` whose document revision is exactly one greater than the input's and whose `validation_result` equals `validate(new_model, rules=RULES)` (Dispatcher Apply Contract unchanged).

`set_generation_profile(model, command)` MUST be purely structural and MUST NEVER raise (DD6). It MUST own exactly the `"profile"` key of `model.generation_metadata[element_id]` (DD156) and MUST evaluate, in order:

| # | Condition | Result |
|---|---|---|
| 1 | `element_id` is neither a class id nor an attribute id of any class | return `model` **unchanged** (DD6), no raise |
| 2 | `command.profile` is truthy (a non-empty mapping) | `entry["profile"] = dict(command.profile)`, every sibling key preserved |
| 3 | `command.profile` is `None` or `{}` | `entry.pop("profile", None)` |
| 4 | the resulting `entry` is empty | drop `metadata[element_id]` entirely |
| 5 | the resulting metadata equals the input | return `model` unchanged (no `dataclasses.replace`) |

The handler MUST NOT touch `classes`, `enumerations`, or `relationships`, and MUST NOT mutate the input model or its metadata mapping. Sibling keys of the entry (for example `source`, `confidence`, or any key other than `"profile"`) MUST be preserved byte-for-byte. Semantic validation of the profile body is NOT the handler's responsibility (it belongs to the write path, see `uml-document-persistence`). **[pytest]**

#### Scenario: Setting a profile on a class id stores it under the "profile" key

- GIVEN a model with class C and empty `generation_metadata`
- WHEN `SetGenerationProfile(C.id, {"auditable": true, "crud": ["create", "read"]})` is applied
- THEN `generation_metadata[C.id] == {"profile": {"auditable": true, "crud": ["create", "read"]}}`
- AND `classes`, `enumerations`, and `relationships` are unchanged **[pytest]**

#### Scenario: Setting a profile on an attribute id stores it under the "profile" key

- GIVEN a model with class C owning attribute A and empty `generation_metadata`
- WHEN `SetGenerationProfile(A.id, {"searchable": true})` is applied
- THEN `generation_metadata[A.id] == {"profile": {"searchable": true}}` **[pytest]**

#### Scenario: Sibling metadata keys are preserved when setting a profile

- GIVEN `generation_metadata[C.id] == {"source": "ai", "confidence": 0.9}`
- WHEN `SetGenerationProfile(C.id, {"auditable": true})` is applied
- THEN `generation_metadata[C.id] == {"source": "ai", "confidence": 0.9, "profile": {"auditable": true}}` **[pytest]**

#### Scenario: Setting a profile replaces a previous profile wholesale

- GIVEN `generation_metadata[C.id] == {"profile": {"auditable": true, "readOnly": true}}`
- WHEN `SetGenerationProfile(C.id, {"crud": ["read"]})` is applied
- THEN `generation_metadata[C.id] == {"profile": {"crud": ["read"]}}` **[pytest]**

#### Scenario: A None profile removes only the "profile" key

- GIVEN `generation_metadata[C.id] == {"source": "ai", "profile": {"auditable": true}}`
- WHEN `SetGenerationProfile(C.id, None)` is applied
- THEN `generation_metadata[C.id] == {"source": "ai"}` **[pytest]**

#### Scenario: An empty mapping profile clears exactly like None

- GIVEN `generation_metadata[C.id] == {"source": "ai", "profile": {"auditable": true}}`
- WHEN `SetGenerationProfile(C.id, {})` is applied
- THEN `generation_metadata[C.id] == {"source": "ai"}` **[pytest]**

#### Scenario: The entry is pruned when the profile was its only key

- GIVEN `generation_metadata == {C.id: {"profile": {"auditable": true}}}`
- WHEN `SetGenerationProfile(C.id, None)` is applied
- THEN `generation_metadata` has no entry for `C.id` (no `{}` residue) **[pytest]**

#### Scenario: A sibling-only entry survives a clear

- GIVEN `generation_metadata == {C.id: {"source": "ai"}}` and no `"profile"` key
- WHEN `SetGenerationProfile(C.id, None)` is applied
- THEN `generation_metadata[C.id] == {"source": "ai"}` **[pytest]**

#### Scenario: An unknown element id is a no-op that never raises

- GIVEN a model with no class or attribute matching id X
- WHEN `SetGenerationProfile(X, {"auditable": true})` and `SetGenerationProfile(X, None)` are each applied
- THEN each resulting model's content equals the input's, `generation_metadata` gains no entry for X, and the revision is exactly one greater than the input's
- AND no exception is raised **[pytest]**

#### Scenario: The input model is never mutated

- GIVEN a model whose `generation_metadata` has an entry for C
- WHEN any `SetGenerationProfile` is applied to C
- THEN the original model instance and its `generation_metadata` mapping are unchanged **[pytest]**

#### Scenario: The command is registered and bumps the revision

- GIVEN a `ProjectDocument` at revision N
- WHEN `apply(document, SetGenerationProfile(C.id, {"auditable": true}))` is called
- THEN the returned `CommandResult.document.revision` is N + 1 and `validation_result` equals `validate(new_model, rules=RULES)` **[pytest]**

### Requirement: Generation Metadata Pruning Primitive

`apps.uml_commands.handlers.generation_profile` MUST expose `prune_generation_metadata(metadata: Mapping[ElementId, Mapping[str, object]], removed_ids: frozenset[ElementId]) -> Mapping[ElementId, Mapping[str, object]]`, shared by the `RemoveClass` and `RemoveAttribute` handlers (DD158). It MUST apply these rules, structurally and without ever raising:

| # | Rule |
|---|---|
| 1 | drop every entry whose key is in `removed_ids` |
| 2 | on every surviving entry, if `entry["profile"]["defaultSort"]["attribute"]` is a `str` whose `ElementId` is in `removed_ids`, pop `"defaultSort"` |
| 3 | if `"profile"` became empty, pop `"profile"`; if the entry became empty, drop the entry |
| 4 | any non-`Mapping` shape encountered on the way down is left untouched — structural only, never raises |
| 5 | return the **same object** when nothing changed, so callers can skip `dataclasses.replace` |

Entries keyed by a relationship id or an operation id MUST NOT be pruned by this primitive or by any remove handler (DD159). **[pytest]**

#### Scenario: Entries keyed by a removed id are dropped

- GIVEN `metadata == {A: {"profile": {"searchable": true}}, B: {"profile": {"auditable": true}}}` and `removed_ids == frozenset({A})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the result is `{B: {"profile": {"auditable": true}}}` **[pytest]**

#### Scenario: A defaultSort pointing at a removed attribute is cleared

- GIVEN `metadata == {C: {"profile": {"auditable": true, "defaultSort": {"attribute": "attr-1", "direction": "asc"}}}}` and `removed_ids == frozenset({ElementId("attr-1")})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the result is `{C: {"profile": {"auditable": true}}}` **[pytest]**

#### Scenario: Empty containers left by pruning are removed

- GIVEN `metadata == {C: {"profile": {"defaultSort": {"attribute": "attr-1", "direction": "asc"}}}}` and `removed_ids == frozenset({ElementId("attr-1")})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN `"profile"` is popped because `defaultSort` was its only key, and the entry for `C` is dropped because `"profile"` was its only key, so the result is `{}` **[pytest]**

#### Scenario: Sibling keys survive when the profile is emptied

- GIVEN `metadata == {C: {"source": "ai", "profile": {"defaultSort": {"attribute": "attr-1", "direction": "asc"}}}}` and `removed_ids == frozenset({ElementId("attr-1")})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the result is `{C: {"source": "ai"}}` **[pytest]**

#### Scenario: Non-Mapping shapes are left untouched and never raise

- GIVEN entries whose `"profile"` is a list, whose `defaultSort` is a string, or whose `defaultSort.attribute` is an integer
- WHEN `prune_generation_metadata` is called with any `removed_ids`
- THEN no exception is raised and those entries are returned untouched **[pytest]**

#### Scenario: A no-change prune returns the same object

- GIVEN `metadata` with no entry keyed by, or `defaultSort`-referencing, any id in `removed_ids` (including empty `metadata`)
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the returned object `is` the input `metadata` **[pytest]**

