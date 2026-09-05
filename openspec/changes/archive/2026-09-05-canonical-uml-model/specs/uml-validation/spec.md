# UML Validation Specification

## Purpose

Defines the single validation engine that inspects any `CanonicalUmlModel` (the project's single convergence point) and produces a navigable, exhaustive diagnostic list. One engine is reused by saving, import, collaboration, assistant, and generation flows.

## Requirements

### Requirement: Single Validation Entry Point

The system MUST expose one function `validate(model: CanonicalUmlModel) -> ValidationResult`. `ValidationResult` MUST expose `diagnostics` (the full list), `errors` (the ERROR-severity subset), and `is_blocking` (true iff any `ERROR` is present).

#### Scenario: Valid model produces no errors
- GIVEN a `CanonicalUmlModel` with no rule violations
- WHEN `validate(model)` is called
- THEN `ValidationResult.errors` is empty and `is_blocking` is `False`

### Requirement: Independently Testable Rule Registry

Each Cycle-1 rule MUST be implemented as an independently testable function `(CanonicalUmlModel) -> Iterable[Diagnostic]`, registered in the engine's rule registry, callable and testable in isolation from the others.

#### Scenario: Rule callable in isolation
- GIVEN a single registered rule function
- WHEN it is invoked directly with a `CanonicalUmlModel`
- THEN it returns its diagnostics without invoking any other rule

### Requirement: Exhaustive Diagnostic Collection

The engine MUST collect diagnostics from every registered rule and MUST NOT short-circuit on the first violation found.

#### Scenario: Multiple violations all reported
- GIVEN a `CanonicalUmlModel` with two unrelated violations (an empty class name and an invalid multiplicity)
- WHEN `validate(model)` is called
- THEN `ValidationResult.diagnostics` contains a diagnostic for both violations

### Requirement: Diagnostic Contract

Each `Diagnostic` MUST carry `severity` (`ERROR` or `WARNING`), a stable SCREAMING_SNAKE `code`, a human-readable `message`, a slash-rooted id-based `path`, and an `element_ref: ElementRef(kind, id) | None`. Every `path` and `element_ref` MUST resolve to an element present in the validated `CanonicalUmlModel`.

#### Scenario: Path and element ref resolve to a real element
- GIVEN a diagnostic raised for attribute `attr-1` on class `class-1`
- WHEN the diagnostic's `path` and `element_ref` are inspected
- THEN `path` equals `/classes/class-1/attributes/attr-1` and `element_ref` equals `ElementRef(kind="attribute", id="attr-1")`, both resolving to elements present in the model

### Requirement: Blocking Policy by Severity

`ERROR` diagnostics MUST block persistence and generation; `WARNING` diagnostics MUST NOT block either.

#### Scenario: Error blocks, warning does not
- GIVEN a `ValidationResult` with one `ERROR` and one `WARNING`
- WHEN `is_blocking` is evaluated
- THEN it is `True` solely due to the `ERROR`, independent of the `WARNING`

### Requirement: Cycle-1 Diagnostic Rule Set

The engine MUST implement exactly the following ten rules against any `CanonicalUmlModel`, with fixed severity:

| Code | Severity |
|---|---|
| `EMPTY_ELEMENT_NAME` | ERROR |
| `DUPLICATE_CLASS_NAME` | ERROR |
| `DUPLICATE_ATTRIBUTE_NAME` | ERROR |
| `DUPLICATE_ENUMERATION_LITERAL` | ERROR |
| `UNKNOWN_ATTRIBUTE_TYPE` | ERROR |
| `INVALID_RELATIONSHIP_ENDPOINT` | ERROR |
| `INVALID_MULTIPLICITY` | ERROR |
| `GENERALIZATION_CYCLE` | ERROR |
| `SELF_ASSOCIATION` | WARNING |
| `CLASS_WITHOUT_ATTRIBUTES` | WARNING |

#### Scenario: EMPTY_ELEMENT_NAME
- GIVEN a class with `name=""`
- WHEN `validate(model)` is called
- THEN an `EMPTY_ELEMENT_NAME` `ERROR` diagnostic is produced for that class

#### Scenario: DUPLICATE_CLASS_NAME
- GIVEN two classes both named `Order`
- WHEN `validate(model)` is called
- THEN a `DUPLICATE_CLASS_NAME` `ERROR` diagnostic is produced

#### Scenario: DUPLICATE_ATTRIBUTE_NAME
- GIVEN one class with two attributes both named `total`
- WHEN `validate(model)` is called
- THEN a `DUPLICATE_ATTRIBUTE_NAME` `ERROR` diagnostic is produced for that class

#### Scenario: DUPLICATE_ENUMERATION_LITERAL
- GIVEN an enumeration with two literals both named `ACTIVE`
- WHEN `validate(model)` is called
- THEN a `DUPLICATE_ENUMERATION_LITERAL` `ERROR` diagnostic is produced

#### Scenario: UNKNOWN_ATTRIBUTE_TYPE
- GIVEN an attribute typed `EnumerationRef("missing-id")` where no enumeration with that id exists
- WHEN `validate(model)` is called
- THEN an `UNKNOWN_ATTRIBUTE_TYPE` `ERROR` diagnostic is produced for that attribute

#### Scenario: INVALID_RELATIONSHIP_ENDPOINT
- GIVEN a relationship whose source id does not match any class in the model
- WHEN `validate(model)` is called
- THEN an `INVALID_RELATIONSHIP_ENDPOINT` `ERROR` diagnostic is produced for that relationship

#### Scenario: INVALID_MULTIPLICITY (negative lower)
- GIVEN a relationship endpoint with `Multiplicity(lower=-1, upper=None)`
- WHEN `validate(model)` is called
- THEN an `INVALID_MULTIPLICITY` `ERROR` diagnostic is produced

#### Scenario: INVALID_MULTIPLICITY (upper below lower)
- GIVEN a relationship endpoint with `Multiplicity(lower=2, upper=1)`
- WHEN `validate(model)` is called
- THEN an `INVALID_MULTIPLICITY` `ERROR` diagnostic is produced, since `upper < lower`

#### Scenario: GENERALIZATION_CYCLE
- GIVEN classes `A` and `B` where `A` generalizes `B` and `B` generalizes `A`
- WHEN `validate(model)` is called
- THEN a `GENERALIZATION_CYCLE` `ERROR` diagnostic is produced

#### Scenario: SELF_ASSOCIATION
- GIVEN an association relationship whose source and target ids are the same class
- WHEN `validate(model)` is called
- THEN a `SELF_ASSOCIATION` `WARNING` diagnostic is produced and does not set `is_blocking`

#### Scenario: CLASS_WITHOUT_ATTRIBUTES
- GIVEN a class with zero attributes
- WHEN `validate(model)` is called
- THEN a `CLASS_WITHOUT_ATTRIBUTES` `WARNING` diagnostic is produced and does not set `is_blocking`
