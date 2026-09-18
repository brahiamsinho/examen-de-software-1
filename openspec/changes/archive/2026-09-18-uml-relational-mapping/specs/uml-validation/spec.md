# Delta for UML Validation

## MODIFIED Requirements

### Requirement: Cycle-1 Diagnostic Rule Set

The engine MUST implement exactly the following twelve rules against any
`CanonicalUmlModel`, with fixed severity:

| Code | Severity |
|---|---|
| `EMPTY_ELEMENT_NAME` | ERROR |
| `DUPLICATE_CLASS_NAME` | ERROR |
| `DUPLICATE_ATTRIBUTE_NAME` | ERROR |
| `DUPLICATE_OPERATION_NAME` | ERROR |
| `DUPLICATE_ENUMERATION_LITERAL` | ERROR |
| `UNKNOWN_ATTRIBUTE_TYPE` | ERROR |
| `INVALID_RELATIONSHIP_ENDPOINT` | ERROR |
| `INVALID_MULTIPLICITY` | ERROR |
| `GENERALIZATION_CYCLE` | ERROR |
| `MULTI_PARENT_GENERALIZATION` | ERROR |
| `SELF_ASSOCIATION` | WARNING |
| `CLASS_WITHOUT_ATTRIBUTES` | WARNING |

(Previously: eleven rules, without `MULTI_PARENT_GENERALIZATION`.)

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

#### Scenario: DUPLICATE_OPERATION_NAME within one class
- GIVEN one class with two operations both named `crearUsuario`, regardless of return type
- WHEN `validate(model)` is called
- THEN a `DUPLICATE_OPERATION_NAME` `ERROR` diagnostic is produced for that class

#### Scenario: Same operation name in different classes is not a duplicate
- GIVEN class A with operation `crearUsuario` and class B with operation `crearUsuario`
- WHEN `validate(model)` is called
- THEN no `DUPLICATE_OPERATION_NAME` diagnostic is produced

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

#### Scenario: MULTI_PARENT_GENERALIZATION
- GIVEN a class `C` with two `GENERALIZATION` relationships as source, targeting distinct classes `A` and `B`
- WHEN `validate(model)` is called
- THEN a `MULTI_PARENT_GENERALIZATION` `ERROR` diagnostic is produced for class `C`

#### Scenario: Single-parent generalization is not flagged
- GIVEN a class `C` with exactly one `GENERALIZATION` relationship as source, targeting `A`
- WHEN `validate(model)` is called
- THEN no `MULTI_PARENT_GENERALIZATION` diagnostic is produced for class `C`

#### Scenario: SELF_ASSOCIATION
- GIVEN an association relationship whose source and target ids are the same class
- WHEN `validate(model)` is called
- THEN a `SELF_ASSOCIATION` `WARNING` diagnostic is produced and does not set `is_blocking`

#### Scenario: CLASS_WITHOUT_ATTRIBUTES
- GIVEN a class with zero attributes
- WHEN `validate(model)` is called
- THEN a `CLASS_WITHOUT_ATTRIBUTES` `WARNING` diagnostic is produced and does not set `is_blocking`

#### Scenario: EMPTY_ELEMENT_NAME still applies to operations
- GIVEN a class with an operation named `""`
- WHEN `validate(model)` is called
- THEN an `EMPTY_ELEMENT_NAME` `ERROR` diagnostic is produced for that operation
