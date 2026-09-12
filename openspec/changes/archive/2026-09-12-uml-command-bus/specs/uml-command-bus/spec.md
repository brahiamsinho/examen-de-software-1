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
endpoint remains.

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

#### Scenario: Attribute is removed
- GIVEN class C with attributes including Attr
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN C's resulting `attributes` no longer contains Attr
- AND the remaining attributes keep their original relative order

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

`RemoveClass`, `RemoveAttribute`, `RemoveRelationship`, and `AddAttribute`
targeting an id absent from the model MUST NOT raise an exception. Each MUST
apply as a no-op — the resulting model's content is identical to the input
— mirroring `CanonicalUmlModel.class_by_id`'s existing None-returning (never
raising) convention for missing lookups. The dispatcher still returns a
`CommandResult` with a new `ProjectDocument` (revision incremented via
`with_model`) and the `ValidationResult` of the unchanged model.

#### Scenario: Removing an unknown class id is a no-op
- GIVEN a model with no class matching id X
- WHEN `RemoveClass(X)` is applied
- THEN the resulting model's classes, enumerations, and relationships are unchanged in content
- AND the resulting document's revision is exactly one greater than the input's
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
