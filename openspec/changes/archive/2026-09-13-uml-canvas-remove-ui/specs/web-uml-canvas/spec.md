# Delta for Web UML Canvas

## ADDED Requirements

### Requirement: Remove Class Command

`RemoveClassControl` MUST offer a class `<select>` and, before submission,
MUST show a confirmation step stating the exact number of relationships
that will cascade-remove, computed client-side as
`relationships.filter(r => r.source.class_id === id || r.target.class_id === id).length`
over `document.model.relationships`. The control MUST NOT submit
`RemoveClass` until the user confirms. On confirmation it MUST submit
`RemoveClass` for the selected class, then refetch the document.

#### Scenario: Confirmation states the exact cascade count

- GIVEN a class with two relationships referencing it as source or target
- WHEN the user selects that class in `RemoveClassControl`
- THEN the confirmation step states exactly 2 relationships will be removed

#### Scenario: Submission is blocked until confirmed

- GIVEN a class is selected and the confirmation step is showing
- WHEN the user has not yet confirmed
- THEN `RemoveClass` is not submitted

#### Scenario: Confirmed removal submits and refetches

- GIVEN a class is selected and the cascade count is shown
- WHEN the user confirms
- THEN `RemoveClass` is submitted for that class and the document is refetched

#### Scenario: Class with no relationships still requires confirmation

- GIVEN a class referenced by zero relationships
- WHEN the user selects that class
- THEN the confirmation step omits the cascade-count line (no relationship
  will be removed) but still requires explicit confirmation before
  `RemoveClass` is submitted

### Requirement: Remove Attribute Command

`RemoveAttributeControl` MUST offer a class `<select>` followed by an
attribute `<select>` scoped to the chosen class's attributes. Submission
MUST send `RemoveAttribute` for the selected class and attribute
immediately, with no confirmation step, then refetch the document.

#### Scenario: Selecting a class populates its attributes

- GIVEN a class with two attributes
- WHEN the user selects that class in `RemoveAttributeControl`
- THEN the attribute `<select>` lists exactly that class's two attributes

#### Scenario: Submission removes immediately without confirmation

- GIVEN a class and one of its attributes are selected
- WHEN the user submits
- THEN `RemoveAttribute` is submitted immediately and the document is
  refetched, with no confirmation step shown

### Requirement: Remove Relationship Command

`RemoveRelationshipControl` MUST offer a relationship `<select>` whose
option labels identify the relationship by its endpoint class names and
kind (`"{sourceName} → {targetName} ({kind})"`, falling back to the raw
class id when a name cannot be resolved), NOT by multiplicity alone —
multiplicity does not disambiguate two relationships between the same
class pair. Submission MUST send `RemoveRelationship` for the selected
relationship immediately, with no confirmation step, then refetch the
document.

#### Scenario: Relationship options are labelled by endpoint names and kind

- GIVEN a relationship of kind `association` from class `Cliente` to
  class `Pedido`
- WHEN `RemoveRelationshipControl` renders its options
- THEN the option label reads "Cliente → Pedido (association)"

#### Scenario: Two relationships between the same classes remain distinguishable

- GIVEN two distinct relationships both linking `Cliente` and `Pedido`
- WHEN `RemoveRelationshipControl` renders its options
- THEN each relationship still appears as its own selectable option

#### Scenario: Submission removes immediately without confirmation

- GIVEN a relationship is selected
- WHEN the user submits
- THEN `RemoveRelationship` is submitted immediately and the document is
  refetched, with no confirmation step shown

### Requirement: Stale Selection Reset After Refetch

Each of `RemoveClassControl`, `RemoveAttributeControl`, and
`RemoveRelationshipControl` MUST NOT crash or submit a stale id when the
document is refetched and the previously selected class, attribute, or
relationship no longer exists (including as a side effect of another
control's cascade removal). Each `<select>` MUST exclude ids absent from
the current document and MUST reset its selection to unset when its
previously selected id disappears.

#### Scenario: Selected relationship is cascade-removed by a class removal

- GIVEN a relationship is selected in `RemoveRelationshipControl`
- WHEN a `RemoveClass` submission elsewhere cascades that relationship away
  and the document refetches
- THEN `RemoveRelationshipControl` resets its selection and does not offer
  or submit the removed relationship id

#### Scenario: Selected class disappears after refetch

- GIVEN a class is selected in `RemoveAttributeControl`
- WHEN that class is removed elsewhere and the document refetches
- THEN `RemoveAttributeControl` resets its class and attribute selections
  without crashing
