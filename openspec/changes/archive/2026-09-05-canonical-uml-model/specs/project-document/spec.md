# Project Document Specification

## Purpose

Defines `ProjectDocument` as the persistence envelope wrapping a `CanonicalUmlModel` (see `uml-domain-model` spec) split into semantic `UmlModel` and visual-only `DiagramLayout`, plus identity, ownership, and revision metadata. Cycle 1 defines shape and pure rules only; no ORM, persistence, or auth.

## Requirements

### Requirement: Project Identity and Metadata

A `ProjectDocument` MUST have a UUID `id`, a `metadata` container (at minimum a project name), and `created_at`/`updated_at` timestamps.

#### Scenario: New document receives a UUID
- GIVEN a new `ProjectDocument` is created
- WHEN its `id` is inspected
- THEN it is a valid UUID and unique per document instance

### Requirement: Opaque Owner Identity

`ProjectDocument.owner_id` MUST be a non-empty `str` that the domain treats as opaque: never interpreted, resolved, or authorized against, and the domain package MUST NOT import `django.contrib.auth` or any auth module.

#### Scenario: Empty owner rejected
- GIVEN an attempt to create a `ProjectDocument` with `owner_id=""`
- WHEN the document is constructed
- THEN the system MUST reject the empty owner id

#### Scenario: Owner id opaque round-trip
- GIVEN `owner_id="42"` set on a `ProjectDocument`
- WHEN the document is read back
- THEN `owner_id` remains the exact string `"42"` with no format transformation or validation beyond non-emptiness

### Requirement: Semantic and Visual Split

`ProjectDocument` MUST hold exactly one `UmlModel` (the semantic `CanonicalUmlModel`, see `uml-domain-model` spec) and exactly one `DiagramLayout` (visual-only, e.g. per-element canvas positions), and the two MUST remain independently modifiable.

#### Scenario: Layout change does not affect model
- GIVEN a `ProjectDocument` with a class and a stored canvas position for it
- WHEN the class's canvas position is moved in `DiagramLayout`
- THEN the `CanonicalUmlModel` classes, attributes, and relationships remain unchanged

#### Scenario: Model change does not require layout change
- GIVEN a `ProjectDocument` with an existing `DiagramLayout`
- WHEN a new attribute is added to the `UmlModel`
- THEN the `DiagramLayout` remains valid and unaffected until a position is explicitly assigned

### Requirement: Pure Revision Increment

`ProjectDocument` MUST expose a `revision` integer field that increments by exactly one on each defined mutation entry point; Cycle 1 defines only the pure increment rule, with no optimistic-concurrency or conflict enforcement.

#### Scenario: Revision increments on mutation
- GIVEN a `ProjectDocument` at `revision=3`
- WHEN a defined mutation is applied
- THEN the resulting `revision` is `4`

#### Scenario: No concurrency enforcement this cycle
- GIVEN two independent in-memory copies of the same `ProjectDocument` at the same `revision`
- WHEN both apply a mutation independently
- THEN the system MUST NOT raise a conflict error, since concurrency enforcement is explicit tech debt for a later cycle
