# Delta for UML Command Bus

## ADDED Requirements

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

## MODIFIED Requirements

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
