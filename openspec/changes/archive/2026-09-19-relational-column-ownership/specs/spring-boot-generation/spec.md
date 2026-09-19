# Delta for Spring Boot Generation

## ADDED Requirements

### Requirement: Column Ownership Metadata Does Not Enable Inheritance Generation

The Spring Boot generator MUST NOT treat `Column.owning_class_id` as support for Java inheritance generation. A table with a discriminator column MUST still be rejected through the existing typed unsupported-table-shape behavior, even when its attribute-derived columns include ownership metadata.

#### Scenario: Discriminator table with ownership metadata is still rejected

- GIVEN a `Table` with a non-`None` `discriminator_column`
- AND at least one attribute-derived `Column` with a non-`None` `owning_class_id`
- WHEN the Spring Boot generator is invoked for that table
- THEN it raises the existing typed unsupported-table-shape error
- AND it produces no Java source for Java inheritance classes
