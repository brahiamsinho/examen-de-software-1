# Delta for Spring Boot Generation

Change: `2026-09-19-spring-boot-project-scaffold`. Adds one requirement and modifies four. Every MODIFIED block below is the COMPLETE replacement of the current main-spec block (all scenarios included), edited in place.

## ADDED Requirements

### Requirement: Project Scaffold Generation

The system MUST provide a pure function `generate_project_scaffold_sources(*, base_package) -> GeneratedSources`, independent of any `Table`, `EnumType` or relational model, that returns exactly three `GeneratedFile`s in this fixed order: `build.gradle`, `settings.gradle`, `src/main/java/<pkg path>/Application.java`, where `<pkg path>` is the validated `base_package` with dots replaced by directory separators. It MUST NOT emit a `.gitignore`, a Gradle wrapper, a Dockerfile, or any other file.

`build.gradle` MUST: apply the `java` plugin and the `org.springframework.boot` plugin at the pinned Spring Boot version; configure a Java toolchain at the pinned Java version (21); declare `mavenCentral()` as the only repository; import the Boot BOM with `implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)`; declare the starters `spring-boot-starter-webmvc`, `spring-boot-starter-data-jpa` and `spring-boot-starter-validation`; declare `runtimeOnly 'org.postgresql:postgresql'`; set `group` equal to `base_package`; and set `version = '0.0.1-SNAPSHOT'`. It MUST NOT declare springdoc/OpenAPI or the `io.spring.dependency-management` plugin. `settings.gradle` MUST set `rootProject.name = 'generated-backend'`. `Application.java` MUST declare `package <base_package>;`, annotate the class `Application` with `@SpringBootApplication`, and declare a `main` method that calls `SpringApplication.run`.

`Application` is NOT a `config/` class. It MUST live in the root base package because `@SpringBootApplication` scans its own package and its sub-packages, so `domain`, `persistence`, `application`, `api` and `errors` are only discovered from the root.

The scaffold MUST NOT contain a hardcoded host, port, URL, credential or absolute path. The pinned Spring Boot and Java versions (and any pinned Gradle runner version) MUST be sourced from one module, so that a version bump changes exactly one place. An invalid `base_package` MUST be rejected by the existing base-package validation, with the same error the other entry points raise, and no file MUST be returned.

#### Scenario: Scaffold yields exactly three files in fixed order

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN the returned file paths are inspected
- THEN the paths are exactly `build.gradle`, `settings.gradle`, `src/main/java/com/example/generated/Application.java`, in that order
- AND no `.gitignore`, Gradle wrapper file or Dockerfile path is present

#### Scenario: Single-segment base package places Application at the shortest path

- GIVEN `generate_project_scaffold_sources(base_package="app")`
- WHEN the returned file paths are inspected
- THEN the third path is `src/main/java/app/Application.java`

#### Scenario: Repeated scaffold generation is byte-identical

- GIVEN the same `base_package`
- WHEN `generate_project_scaffold_sources` is invoked twice
- THEN both returned `GeneratedSources` values are equal
- AND every corresponding file has the same path and byte-identical content

#### Scenario: build.gradle declares the verified plugins, toolchain and repository

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN the content of `build.gradle` is inspected
- THEN it applies the `java` and `org.springframework.boot` plugins with the pinned Boot version
- AND it sets the Java toolchain to 21 and declares only `mavenCentral()` as a repository
- AND it contains `implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)`

#### Scenario: build.gradle declares the verified starters and driver only

- GIVEN the same scaffold
- WHEN the dependency declarations in `build.gradle` are inspected
- THEN `spring-boot-starter-webmvc`, `spring-boot-starter-data-jpa` and `spring-boot-starter-validation` are declared
- AND `runtimeOnly 'org.postgresql:postgresql'` is declared
- AND the content contains no `springdoc` and no `io.spring.dependency-management`

#### Scenario: build.gradle carries group and version, settings.gradle carries the project name

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN `build.gradle` and `settings.gradle` are inspected
- THEN `build.gradle` sets `group` to `com.example.generated` and `version = '0.0.1-SNAPSHOT'`
- AND `settings.gradle` sets `rootProject.name = 'generated-backend'`

#### Scenario: Application.java is a Spring Boot entry point in the root package

- GIVEN `generate_project_scaffold_sources(base_package="com.example.generated")`
- WHEN the content of `Application.java` is inspected
- THEN it declares `package com.example.generated;`, a class `Application` annotated `@SpringBootApplication`, and a `main` method calling `SpringApplication.run`
- AND its package equals the `group` in `build.gradle`, so component scanning covers every generated layer package

#### Scenario: No scaffold file hardcodes deployable values

- GIVEN the three scaffold files
- WHEN their content is scanned
- THEN no file contains a URL scheme (`http://`, `https://`), `localhost`, an IP address, a port number, a username or password value, or an absolute filesystem path
- AND `build.gradle` names no repository other than `mavenCentral()`

#### Scenario: Pinned versions come from one module

- GIVEN the pinned Spring Boot and Java versions declared in the single versions module
- WHEN the scaffold is generated and the emit package sources are inspected
- THEN the Boot version in `build.gradle` equals the module's Boot value and the toolchain version equals its Java value
- AND each pinned version literal is defined in that module only, not in the renderer, templates or other emit modules

#### Scenario: Invalid base package is rejected without output

- GIVEN a `base_package` that fails the existing validation (for example `Com.Example`, `com-example`, `com..example`, an empty string, or a Java-invalid leading digit segment)
- WHEN `generate_project_scaffold_sources` is invoked
- THEN it raises the same error the existing base-package validation raises for the other entry points
- AND no `GeneratedSources` is returned

#### Scenario: Project aggregate is the model aggregate followed by the scaffold

- GIVEN a valid `RelationalModel` and `base_package="com.example.generated"`
- WHEN `generate_project_sources(model, base_package="com.example.generated")` is invoked
- THEN the returned files are exactly the files of `generate_model_sources(model, base_package="com.example.generated")` in their own order, followed by the three scaffold files in scaffold order
- AND the three trailing files are identical to the output of `generate_project_scaffold_sources` for the same `base_package`
- AND `generate_model_sources` returns the same output as before this change

#### Scenario: Empty model still yields the full project

- GIVEN an empty `RelationalModel`
- WHEN `generate_project_sources(model, base_package="com.example.generated")` is invoked
- THEN the returned files are the shared error files, `src/main/resources/application.yml`, then the three scaffold files

#### Scenario: Project aggregate rejects an invalid base package

- GIVEN a valid `RelationalModel` and an invalid `base_package`
- WHEN `generate_project_sources` is invoked
- THEN the same base-package validation error is raised
- AND no `GeneratedSources` is returned

## MODIFIED Requirements

### Requirement: Package and File Path Layout

Generated Java files MUST be placed only under the `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`), with exactly one exception: the single project entry-point class `src/main/java/<pkg path>/Application.java`, which sits directly in the root base package and is emitted only by `generate_project_scaffold_sources` (and therefore by `generate_project_sources`). `Application` is NOT a `config/` class; it MUST live in the root base package because `@SpringBootApplication` scans its own package downward. Two non-Java root files, `build.gradle` and `settings.gradle`, are likewise emitted only by those scaffold entry points. The `validation/` and Java `config/` subdirectories MUST NOT be produced by this slice. For non-discriminator tables, `generate_table_sources(table, *, base_package)` MUST emit exactly six files per call, in fixed layer order: `domain/<E>.java`, `persistence/<E>Repository.java`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, `api/<E>Controller.java`. For supported discriminator-backed tables, `generate_table_sources(table, *, base_package)` MUST emit only `domain/` entity classes and the root `persistence/` repository according to the inheritance artifact boundary. A separate `generate_shared_error_sources(*, base_package)` entry point, taking no `Table`, MUST emit exactly two per-project Java files: `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`. A separate `generate_project_config_sources()` entry point, taking no `Table`, `EnumType`, relational model, base package, or application name, MUST emit exactly one resource file at `src/main/resources/application.yml`. `generate_table_sources` MUST NOT emit any file under `errors/` or `src/main/resources/`. `generate_table_sources`, `generate_shared_error_sources` and `generate_project_config_sources` MUST NOT emit any scaffold path (`build.gradle`, `settings.gradle`, `src/main/java/<pkg path>/Application.java`).

(Previously: Java files were allowed only under the six layer directories with no exception, and no root-level build files were described. Now the root-package `Application.java` is the single Java file outside the layers, `build.gradle` and `settings.gradle` are the two allowed root files, and the three existing entry points are explicitly barred from emitting scaffold paths.)

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

- GIVEN the `Product` table generated end to end, the shared error sources generated once, the project singleton configuration generated once, and the project scaffold generated once
- WHEN the combined set of emitted file paths is inspected
- THEN no file exists under `validation/` or `config/`
- AND `Application.java` is not under any `config/` directory

#### Scenario: Project application YAML is emitted only by the project singleton configuration generator

- GIVEN table generation, shared error generation, enum generation, and project singleton configuration generation are each invoked through their own entry point
- WHEN all returned file paths are inspected
- THEN only the project singleton configuration generator emits `src/main/resources/application.yml`
- AND no other generator emits a path under `src/main/resources/`

#### Scenario: Application.java is the single Java file outside the six layer directories

- GIVEN `generate_project_sources(model, base_package="com.example.generated")` for a model with tables, enums and shared errors
- WHEN every emitted `.java` path is classified
- THEN every path is under one of the six layer directories, except `src/main/java/com/example/generated/Application.java`, which is directly in the root base package
- AND the only non-Java, non-resource root files are `build.gradle` and `settings.gradle`

#### Scenario: Existing entry points never emit scaffold paths

- GIVEN `generate_table_sources` for a non-discriminator table and a discriminator-backed table, `generate_shared_error_sources`, and `generate_project_config_sources` are each invoked
- WHEN all returned file paths are inspected
- THEN none of them equals `build.gradle`, `settings.gradle`, or ends with `/Application.java` at the root base package

### Requirement: Generator Purity

The generator MUST be a pure function of its in-memory inputs to generated source text. It MUST NOT call `relational_mapping`'s `validate()` or any validation routine, and MUST NOT open, query, or otherwise touch any database connection. The project configuration generator MUST also avoid filesystem writes, environment-variable inspection, subprocess execution, Java compilation, Gradle execution, and network access. The project scaffold entry points (`generate_project_scaffold_sources` and `generate_project_sources`) MUST avoid the same: filesystem access, environment-variable inspection, subprocess execution, network access, Java compilation, and Gradle execution. Emitting `build.gradle` text is string rendering only; no Gradle process is started.

(Previously: the extra filesystem/environment/subprocess/compilation/Gradle/network restriction was stated only for the project configuration generator.)

#### Scenario: Generation succeeds with no DB and no validation call
- GIVEN a valid in-memory `Table` and no database connection available in the test process
- WHEN the entity and repository are generated
- THEN generation completes and returns Java source text, with no validation function invoked and no DB access attempted

#### Scenario: Scaffold and project generation are runtime-free

- GIVEN a valid `base_package`, a valid in-memory `RelationalModel`, and a test process with no project directory, database, JVM or Gradle available
- WHEN `generate_project_scaffold_sources` and `generate_project_sources` are invoked
- THEN both succeed using only in-memory inputs
- AND no filesystem access, environment read, subprocess, network access, Java compilation, Gradle execution, database access, or validation call occurs

### Requirement: Whole-Model Duplicate Path Rejection

Before returning a whole-model aggregate, the system MUST reject any exact duplicate `GeneratedFile.path` across all generated table, enum, shared error, and project configuration artifacts. The same atomic, typed rejection MUST apply to `generate_project_sources`, across the `generate_model_sources` artifacts and the three scaffold artifacts combined. Duplicate path rejection MUST raise a typed generator error under the existing `UngeneratableSourceError` family (`GeneratedSourcePathCollisionError`). On duplicate path failure, the system MUST NOT return a partial `GeneratedSources`, MUST NOT overwrite any file, MUST NOT deduplicate files, and MUST NOT silently keep the first or last occurrence.

(Previously: the rejection was specified for the whole-model aggregate only; `generate_project_sources` did not exist. Note: with the current renderers a model class cannot produce a scaffold path, since even a UML class named `Application` renders to `domain/Application.java`, so the project-level check is a structural invariant and is specified through injected duplicates.)

#### Scenario: Duplicate exact output path fails atomically

- GIVEN a `RelationalModel` containing two source artifacts that would produce the same exact generated output path
- WHEN `generate_model_sources(model)` is invoked
- THEN a typed duplicate-path generator error is raised
- AND no `GeneratedSources` aggregate is returned
- AND no partial result is exposed to the caller

#### Scenario: Project aggregate rejects two generated files sharing an exact path

- GIVEN two generated files that share an exact path, presented to the project aggregate's combination step
- WHEN they are combined by the project aggregate
- THEN `GeneratedSourcePathCollisionError` is raised
- AND no `GeneratedSources` is returned and no partial result is exposed

#### Scenario: Model-level duplicate propagates through the project aggregate

- GIVEN a `RelationalModel` whose model artifacts already contain a duplicate exact path
- WHEN `generate_project_sources(model)` is invoked
- THEN the same typed `GeneratedSourcePathCollisionError` is raised
- AND no scaffold file or partial aggregate is returned

### Requirement: Existing Generator Contracts Are Preserved

Whole-model generation MUST preserve all existing table, enum, shared-error, and project-configuration generator contracts. It MUST NOT change lower-level generated paths, generated content, file ordering inside each lower-level generator result, supported inheritance table behavior, unsupported-shape typed errors, package propagation rules, or project configuration placeholders. `generate_model_sources` MUST NOT add OpenAPI, Postman, Domain Manifest, filtering/search metadata, generated filtering APIs, inheritance API expansion, frontend output, mobile output, Java `config/` classes, filesystem writing, project materialization, compilation, Docker behavior, or any Gradle artifact (`build.gradle`, `settings.gradle`, wrapper), and its output MUST remain byte-identical to its output before the project scaffold change. This prohibition is scoped to `generate_model_sources`. Emitting Gradle build text from a different entry point (`generate_project_scaffold_sources`, `generate_project_sources`) is not "Gradle behavior" in the sense of this requirement, because no Gradle is executed, and it does not alter any lower-level generator contract.

(Previously: the ban on Docker and Gradle artifacts was stated for whole-model generation in general, with no distinction between `generate_model_sources` and later project-level entry points.)

#### Scenario: Lower-level generator outputs are unchanged inside the aggregate

- GIVEN a supported `Table`, a supported `EnumType`, the shared error source set, and the project configuration source set
- WHEN each lower-level generator is invoked directly and the same inputs are also generated through `generate_model_sources`
- THEN the corresponding files inside the whole-model aggregate have the same paths, ordering within their own generator boundary, and byte-identical content as the direct lower-level generator outputs
- AND the whole-model aggregate contains no out-of-scope OpenAPI, Postman, Manifest, filtering, frontend, mobile, Java `config/`, materialization, compilation, Docker, or Gradle artifact

#### Scenario: generate_model_sources output contains no scaffold path

- GIVEN any valid `RelationalModel` and `base_package`
- WHEN `generate_model_sources` is invoked
- THEN no returned path equals `build.gradle` or `settings.gradle`, and no returned path is the root-package `Application.java`
- AND the returned files and their order are identical to the pre-change output for the same input

#### Scenario: Project-level Gradle text does not change the model aggregate

- GIVEN `generate_project_sources(model, base_package=...)` and `generate_model_sources(model, base_package=...)` for the same inputs
- WHEN both are invoked
- THEN the leading files of the project aggregate equal the model aggregate exactly
- AND only the trailing three scaffold files are added by the project entry point
