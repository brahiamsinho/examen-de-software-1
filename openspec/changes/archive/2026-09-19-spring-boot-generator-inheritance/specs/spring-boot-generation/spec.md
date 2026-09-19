# Delta for Spring Boot Generation

## ADDED Requirements

### Requirement: Discriminator-Backed Single Table Domain Generation

For a supported discriminator-backed `Table`, `generate_table_sources(table, *, base_package)` MUST generate JPA Single Table inheritance domain source plus one root Spring Data repository. The supported shape MUST have a single UUID primary key, a non-empty `source_class_ids` sequence whose first entry is the root class id, a non-`None` `discriminator_column`, discriminator values for every generated hierarchy class id, and only columns that can be assigned to the root entity, a subclass entity, a supported single-column relationship field, an enum field, the synthetic id, or discriminator metadata. The generator MUST use the discriminator column as JPA inheritance metadata and MUST NOT emit it as a normal Java field on any generated class.

#### Scenario: Supported discriminator table yields root entity, subclass entities, and root repository

- GIVEN a `Table` named `Vehicle` with a UUID primary key, `source_class_ids=("vehicle", "car", "truck")`, `discriminator_column="class_type"`, discriminator values for `vehicle`, `car`, and `truck`, root-owned scalar columns, and subclass-owned scalar columns
- WHEN `generate_table_sources` is invoked for the table
- THEN generation succeeds
- AND the emitted files contain `domain/Vehicle.java`, `domain/Car.java`, `domain/Truck.java`, and `persistence/VehicleRepository.java`
- AND no emitted Java class declares a normal field for `class_type`

#### Scenario: Actual discriminator column name is used as metadata

- GIVEN a supported discriminator-backed `Table` whose discriminator column is named `kind`
- WHEN the root entity source is emitted
- THEN the root entity declares discriminator metadata using the name `kind`
- AND no generated entity declares `kind` as a normal Java field

### Requirement: Root and Subclass JPA Inheritance Annotations

For a supported discriminator-backed `Table`, the root entity MUST be annotated with `@Entity`, `@Table(name = "...")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, and `@DiscriminatorColumn(name = "...")`. The root entity MUST include `@DiscriminatorValue("...")` when `Table.discriminator_values` contains a value for the root class id. The root entity MUST be generated as non-abstract unless later UML metadata explicitly exposes abstract-class semantics. Each subclass entity MUST be annotated with `@Entity` and `@DiscriminatorValue("...")`, MUST extend the root entity Java class, and MUST NOT redeclare the inherited id or root-owned fields.

#### Scenario: Root entity contains Single Table metadata

- GIVEN a supported discriminator-backed `Vehicle` table with discriminator column `class_type` and root discriminator value `VEHICLE`
- WHEN the root entity source is emitted
- THEN `Vehicle.java` contains `@Entity`, `@Table(name = "Vehicle")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, `@DiscriminatorColumn(name = "class_type")`, and `@DiscriminatorValue("VEHICLE")`
- AND `Vehicle` is not declared `abstract`

#### Scenario: Subclass entity extends the root and declares its discriminator value

- GIVEN the same table has a subclass class id `car` with discriminator value `CAR`
- WHEN the subclass entity source is emitted
- THEN `Car.java` contains `@Entity` and `@DiscriminatorValue("CAR")`
- AND the class declaration extends `Vehicle`
- AND `Car.java` does not redeclare the UUID id field

### Requirement: Field Ownership Partitioning for Inheritance Entities

For a supported discriminator-backed `Table`, the generator MUST partition entity fields by `Column.owning_class_id`. Attribute-derived columns whose `owning_class_id` is the root class id MUST be emitted only on the root entity. Attribute-derived columns whose `owning_class_id` is a subclass class id MUST be emitted only on that subclass entity. A subclass entity MUST NOT duplicate root-owned fields or fields owned by another subclass. Supported structural columns with no `owning_class_id`, such as the synthetic primary key, MUST be assigned according to their structural role. Unsupported non-discriminator, non-primary-key columns without an assignable ownership role MUST be rejected with a typed error before rendering.

#### Scenario: Root-owned attribute renders only on the root entity

- GIVEN a supported discriminator-backed `Vehicle` table with root-owned column `vin`
- WHEN inheritance domain sources are emitted
- THEN `Vehicle.java` declares field `vin`
- AND no subclass entity declares field `vin`

#### Scenario: Subclass-owned attribute renders only on the matching subclass entity

- GIVEN a supported discriminator-backed `Vehicle` table with `car`-owned column `door_count` and `truck`-owned column `payload_capacity`
- WHEN inheritance domain sources are emitted
- THEN `Car.java` declares `doorCount` and does not declare `payloadCapacity`
- AND `Truck.java` declares `payloadCapacity` and does not declare `doorCount`
- AND `Vehicle.java` declares neither subclass-owned field

### Requirement: Inheritance Artifact Boundary and Deterministic File Order

For a supported discriminator-backed `Table`, `generate_table_sources` MUST emit only the root entity, concrete subclass entities, and the root repository. It MUST emit files in deterministic order: root entity first, subclass entities in `Table.source_class_ids` order excluding the root class id, and root repository last. It MUST NOT emit request DTOs, response DTOs, services, controllers, subclass repositories, shared error sources, configuration, OpenAPI, Postman, Domain Manifest, or any non-Java infrastructure artifact for the discriminator-backed table.

#### Scenario: Inheritance files are emitted in deterministic hierarchy order

- GIVEN a supported discriminator-backed `Vehicle` table with `source_class_ids=("vehicle", "car", "truck")`
- WHEN `generate_table_sources` is invoked twice for the same table
- THEN both invocations return files in the exact order `domain/Vehicle.java`, `domain/Car.java`, `domain/Truck.java`, `persistence/VehicleRepository.java`
- AND each corresponding file's source text is byte-identical across invocations

#### Scenario: DTO service controller and subclass repositories are omitted

- GIVEN a supported discriminator-backed `Vehicle` table with subclasses `Car` and `Truck`
- WHEN `generate_table_sources` is invoked
- THEN no emitted path is under `application/`, `application/dto/`, `api/`, `errors/`, `validation/`, or `config/`
- AND no emitted path ends with `CarRepository.java` or `TruckRepository.java`

### Requirement: Root Repository for Inheritance Hierarchy

For a supported discriminator-backed `Table`, the generator MUST produce exactly one Spring Data JPA repository interface for the root entity type and UUID id type. The repository MUST be named from the root entity Java class name and MUST rely on JPA polymorphism rather than generated subclass repositories.

#### Scenario: Root repository is parameterized by the root entity

- GIVEN a supported discriminator-backed `Vehicle` table with subclasses `Car` and `Truck`
- WHEN repository source is emitted
- THEN `persistence/VehicleRepository.java` declares `VehicleRepository`
- AND the repository extends a Spring Data repository parameterized with `<Vehicle, UUID>`
- AND no repository source is emitted for `Car` or `Truck`

### Requirement: Exact Backward Compatibility for Non-Discriminator Table Generation

For any table with no discriminator inheritance metadata, `generate_table_sources(table, *, base_package)` MUST preserve the existing non-inheritance contract exactly. It MUST emit the same six files, in the same order, at the same paths, with byte-identical Java source text compared to the pre-inheritance implementation for the same supported non-discriminator input.

#### Scenario: Non-discriminator table output remains byte-identical

- GIVEN a supported non-discriminator `Product` table that generated six files before inheritance support
- WHEN `generate_table_sources` is invoked after inheritance support is added
- THEN exactly the same six paths are emitted in the same order
- AND every emitted file's Java source text is byte-identical to the pre-inheritance output

## MODIFIED Requirements

### Requirement: Rejection of Unsupported Table Shapes

The system MUST raise a typed error, and MUST NOT emit partial or malformed Java source, when the input `Table` contains a construct out of scope for the applicable generation path: a primary key that is not a single UUID column, a `ForeignKey` whose `column_names` has more than one entry (composite FK), or malformed/unsupported discriminator-backed inheritance metadata. A non-empty `foreign_keys` with only single-column entries, and a `Column` with a non-`None` `enum_type_name`, MUST NOT be rejected solely for those reasons — both are supported and MUST be generated per the applicable entity-generation requirements. A discriminator-backed table MUST NOT be rejected merely because `discriminator_column` or `discriminator_values` is present when it satisfies the supported Single Table inheritance shape.

(Previously: any table with a non-`None` `discriminator_column` was rejected, even when the table carried ownership metadata and otherwise represented the mapper's Single Table inheritance shape.)

#### Scenario: Table with a foreign key is accepted

- GIVEN a `Table` whose `foreign_keys` is non-empty and every `ForeignKey.column_names` has exactly one entry
- WHEN the generator is invoked on it
- THEN it does not raise a rejection error and proceeds to emit the entity with the corresponding relationship field(s)

#### Scenario: Table with a composite foreign key is rejected

- GIVEN a `Table` containing a `ForeignKey` whose `column_names` has more than one entry
- WHEN the generator is invoked on it
- THEN it raises a typed error and produces no Java source

#### Scenario: Supported discriminator table is accepted

- GIVEN a discriminator-backed `Table` satisfying the supported Single Table inheritance shape
- WHEN the generator is invoked on it
- THEN it does not raise an inheritance-unsupported error
- AND it emits only inheritance domain classes plus the root repository

#### Scenario: Malformed discriminator table missing class ids is rejected

- GIVEN a `Table` with a discriminator column but an empty `source_class_ids` sequence
- WHEN the generator is invoked on it
- THEN it raises a typed malformed-inheritance error
- AND it produces no Java source

#### Scenario: Malformed discriminator table missing a discriminator value is rejected

- GIVEN a `Table` with `source_class_ids` containing `vehicle` and `car`
- AND `Table.discriminator_values` has no value for `car`
- WHEN the generator is invoked on it
- THEN it raises a typed malformed-inheritance error
- AND it produces no Java source

#### Scenario: Unsupported ownership shape is rejected before rendering

- GIVEN a discriminator-backed `Table` with an attribute-derived column whose `owning_class_id` is not present in `source_class_ids`
- WHEN the generator is invoked on it
- THEN it raises a typed malformed-inheritance error
- AND it produces no Java source

#### Scenario: Table with an enum-typed column is accepted

- GIVEN a `Table` containing a `Column` with `enum_type_name` set
- WHEN the generator is invoked on it
- THEN it does not raise a rejection error and proceeds to emit the entity with the corresponding enum field

### Requirement: Package and File Path Layout

Generated files MUST be placed only under the `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`). The `validation/` and `config/` subdirectories MUST NOT be produced by this slice. For non-discriminator tables, `generate_table_sources(table, *, base_package)` MUST emit exactly six files per call, in fixed layer order: `domain/<E>.java`, `persistence/<E>Repository.java`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, `api/<E>Controller.java`. For supported discriminator-backed tables, `generate_table_sources(table, *, base_package)` MUST emit only `domain/` entity classes and the root `persistence/` repository according to the inheritance artifact boundary. A separate `generate_shared_error_sources(*, base_package)` entry point, taking no `Table`, MUST emit exactly two per-project files: `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`. `generate_table_sources` MUST NOT emit any file under `errors/`.

(Previously: `generate_table_sources` emitted exactly six files for every accepted table and any table with a discriminator column was rejected.)

#### Scenario: A non-discriminator table yields six layered files under domain, persistence, application, and api

- GIVEN the `Product` table generated end to end via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN exactly six files exist, one each at `domain/`, `persistence/`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, and `api/<E>Controller.java`, in that fixed order

#### Scenario: A discriminator-backed table yields only domain and root persistence files

- GIVEN a supported discriminator-backed `Vehicle` table generated via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN every emitted path is under `domain/` or is the root repository under `persistence/`
- AND no DTO, service, controller, shared error, validation, or config path is emitted

#### Scenario: Error sources are emitted only by the shared entry point

- GIVEN `generate_shared_error_sources(base_package=...)` is invoked
- WHEN the returned files are inspected
- THEN exactly two files exist under `errors/`, and no file under `errors/` is produced by any `generate_table_sources` call

#### Scenario: Validation and config directories remain forbidden

- GIVEN the `Product` table generated end to end and the shared error sources generated once
- WHEN the combined set of emitted file paths is inspected
- THEN no file exists under `validation/` or `config/`

### Requirement: Column Ownership Metadata Does Not Enable Inheritance Generation

The Spring Boot generator MUST use `Column.owning_class_id` to place attribute-derived columns on the correct entity class for supported discriminator-backed Single Table inheritance generation. This ownership metadata MUST NOT enable DTO, service, controller, subclass repository, relationship-ownership, or whole-model orchestration behavior for inheritance tables in this slice. Unsupported ownership shapes MUST still be rejected through typed unsupported-table-shape behavior before rendering.

(Previously: the generator did not treat `Column.owning_class_id` as support for Java inheritance generation and rejected any table with a discriminator column.)

#### Scenario: Discriminator table with ownership metadata generates bounded inheritance artifacts

- GIVEN a supported discriminator-backed `Table` with at least one root-owned attribute-derived `Column` and one subclass-owned attribute-derived `Column`
- WHEN the Spring Boot generator is invoked for that table
- THEN it emits Java inheritance domain classes with fields partitioned by `owning_class_id`
- AND it emits the root repository
- AND it produces no Java source for inheritance DTOs, services, controllers, or subclass repositories

#### Scenario: Ownership metadata outside the hierarchy is rejected

- GIVEN a discriminator-backed `Table` with an attribute-derived `Column.owning_class_id` that is not present in `Table.source_class_ids`
- WHEN the Spring Boot generator is invoked for that table
- THEN it raises a typed unsupported-table-shape error
- AND it produces no Java source for Java inheritance classes
