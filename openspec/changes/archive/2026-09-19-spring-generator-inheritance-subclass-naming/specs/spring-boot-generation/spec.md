# Delta for Spring Boot Generation

## MODIFIED Requirements

### Requirement: Discriminator-Backed Single Table Domain Generation

For a supported discriminator-backed `Table`, `generate_table_sources(table, *, base_package)` MUST generate JPA Single Table inheritance domain source plus one root Spring Data repository. The supported shape MUST have a single UUID primary key, a non-empty `source_class_ids` sequence whose first entry is the root class id, a non-`None` `discriminator_column`, discriminator values for every generated hierarchy class id, and only columns that can be assigned to the root entity, a subclass entity, a supported single-column relationship field, an enum field, the synthetic id, or discriminator metadata. The generator MUST use the discriminator column as JPA inheritance metadata and MUST NOT emit it as a normal Java field on any generated class. The Java class name of each subclass entity MUST be `pascal_case` of `Table.discriminator_values[class_id]` (the UML class name) and MUST NOT be derived from the class id; the root entity name remains `pascal_case(Table.name)`. A subclass name that is not a valid Java identifier MUST keep raising the existing typed `InvalidJavaIdentifierError`.
(Previously: the requirement did not state how the subclass Java class name is derived, and the implementation derived it from the class id.)

#### Scenario: Supported discriminator table yields root entity, subclass entities, and root repository

- GIVEN a `Table` named `Vehicle` with a UUID primary key, `source_class_ids=("vehicle", "car", "truck")`, `discriminator_column="class_type"`, discriminator values `Vehicle`, `Car`, and `Truck` for those ids, root-owned scalar columns, and subclass-owned scalar columns
- WHEN `generate_table_sources` is invoked for the table
- THEN generation succeeds
- AND the emitted files contain `domain/Vehicle.java`, `domain/Car.java`, `domain/Truck.java`, and `persistence/VehicleRepository.java`
- AND no emitted Java class declares a normal field for `class_type`

#### Scenario: Actual discriminator column name is used as metadata

- GIVEN a supported discriminator-backed `Table` whose discriminator column is named `kind`
- WHEN the root entity source is emitted
- THEN the root entity declares discriminator metadata using the name `kind`
- AND no generated entity declares `kind` as a normal Java field

#### Scenario: Uuid-hex class ids generate subclasses named from the UML class name

- GIVEN a hierarchy whose class ids are `new_id()` uuid hex strings (some starting with a digit) and discriminator values `Vehicle`, `Car`, `Truck`
- WHEN `generate_project_sources` and `generate_model_sources` are invoked for the model
- THEN generation succeeds without `InvalidJavaIdentifierError`
- AND the emitted files include `domain/Car.java` and `domain/Truck.java`

#### Scenario: Subclass name does not depend on the class id

- GIVEN two otherwise identical tables whose class ids differ (readable ids versus uuid hex ids) with the same discriminator values
- WHEN `generate_table_sources` is invoked for each table
- THEN both return the same paths and byte-identical Java source text

#### Scenario: Class name that is not a valid Java identifier is rejected

- GIVEN a subclass whose discriminator value is `Electric Car`
- WHEN the Spring Boot generator is invoked for the table
- THEN it raises `InvalidJavaIdentifierError`
- AND this is a documented known limitation with no sanitizing behavior

### Requirement: Root and Subclass JPA Inheritance Annotations

For a supported discriminator-backed `Table`, the root entity MUST be annotated with `@Entity`, `@Table(name = "...")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, and `@DiscriminatorColumn(name = "...")`. The root entity MUST include `@DiscriminatorValue("...")` when `Table.discriminator_values` contains a value for the root class id. The root entity MUST be generated as non-abstract unless later UML metadata explicitly exposes abstract-class semantics. Each subclass entity MUST be annotated with `@Entity` and `@DiscriminatorValue("...")`, MUST extend the root entity Java class, and MUST NOT redeclare the inherited id or root-owned fields.
(Previously: unchanged text; scenarios used discriminator values `VEHICLE` and `CAR`, which coupled the file name to the value casing.)

#### Scenario: Root entity contains Single Table metadata

- GIVEN a supported discriminator-backed `Vehicle` table with discriminator column `class_type` and root discriminator value `Vehicle`
- WHEN the root entity source is emitted
- THEN `Vehicle.java` contains `@Entity`, `@Table(name = "Vehicle")`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, `@DiscriminatorColumn(name = "class_type")`, and `@DiscriminatorValue("Vehicle")`
- AND `Vehicle` is not declared `abstract`

#### Scenario: Subclass entity extends the root and declares its discriminator value

- GIVEN the same table has a subclass class id `car` with discriminator value `Car`
- WHEN the subclass entity source is emitted
- THEN `Car.java` contains `@Entity` and `@DiscriminatorValue("Car")`
- AND the class declaration extends `Vehicle`
- AND `Car.java` does not redeclare the UUID id field
