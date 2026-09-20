# Delta for Spring Boot Generation

Lines ~243 (`application.yml` MUST NOT emit OpenAPI) and ~609 (model aggregate has no OpenAPI artifact) stay true: a declared dependency is not an emitted OpenAPI artifact. No change there.

## MODIFIED Purpose

Defines the pure, deterministic Spring Boot source emission already implemented for the generated backend stack: one-table Java generation, enum generation, shared error Java generation, bounded Single Table inheritance Java generation, one project-singleton `application.yml` resource, and project scaffold generation (`build.gradle`, `settings.gradle`, root-package `Application.java`). The system provides a project aggregate via `generate_project_sources` that combines the model aggregate with the project scaffold. Java compilation, Postman, Domain Manifest, generated frontend/mobile output, generated-project materialization, and Java `config/` classes remain out of scope. OpenAPI output is out of scope only as an emitted artifact or configuration (no OpenAPI file, no OpenAPI YAML keys, no OpenAPI Java config); the scaffold MAY declare the springdoc dependency so the running generated app serves its own document. Whole-model and project orchestration are now supported as in-memory aggregate APIs.

(Previously: "Java compilation, OpenAPI, Postman, ..." listed OpenAPI wholesale as out of scope.)

## MODIFIED Requirements

### Requirement: Project Scaffold Generation

The system MUST provide a pure function `generate_project_scaffold_sources(*, base_package) -> GeneratedSources`, independent of any `Table`, `EnumType` or relational model, that returns exactly three `GeneratedFile`s in this fixed order: `build.gradle`, `settings.gradle`, `src/main/java/<pkg path>/Application.java`, where `<pkg path>` is the validated `base_package` with dots replaced by directory separators. It MUST NOT emit a `.gitignore`, a Gradle wrapper, a Dockerfile, or any other file.

`build.gradle` MUST: apply the `java` plugin and the `org.springframework.boot` plugin at the pinned Spring Boot version; configure a Java toolchain at the pinned Java version (21); declare `mavenCentral()` as the only repository; import the Boot BOM with `implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)`; declare the starters `spring-boot-starter-webmvc`, `spring-boot-starter-data-jpa` and `spring-boot-starter-validation`; declare `implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:<springdoc version>'`, where the version is rendered from a single-sourced `SPRINGDOC_VERSION` (3.1.1) in `emit/versions.py` and carried via `BuildScriptContext.springdoc_version` (the Boot BOM does not manage springdoc); declare `runtimeOnly 'org.postgresql:postgresql'`; set `group` equal to `base_package`; and set `version = '0.0.1-SNAPSHOT'`. It MUST NOT declare the `io.spring.dependency-management` plugin, a Swagger UI starter (`springdoc-openapi-starter-webmvc-ui`), or actuator. `settings.gradle` MUST set `rootProject.name = 'generated-backend'`. `Application.java` MUST declare `package <base_package>;`, annotate the class `Application` with `@SpringBootApplication`, and declare a `main` method that calls `SpringApplication.run`.

(Previously: `build.gradle` MUST NOT declare springdoc/OpenAPI; no springdoc version constant existed.)

`Application` is NOT a `config/` class. It MUST live in the root base package because `@SpringBootApplication` scans its own package and its sub-packages, so `domain`, `persistence`, `application`, `api` and `errors` are only discovered from the root.

The scaffold MUST NOT contain a hardcoded host, port, URL, credential or absolute path. The pinned Spring Boot, Java and springdoc versions (and any pinned Gradle runner version) MUST be sourced from one module, so that a version bump changes exactly one place. An invalid `base_package` MUST be rejected by the existing base-package validation, with the same error the other entry points raise, and no file MUST be returned.

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

#### Scenario: build.gradle declares the verified starters, springdoc and driver only

- GIVEN the same scaffold
- WHEN the dependency declarations in `build.gradle` are inspected
- THEN `spring-boot-starter-webmvc`, `spring-boot-starter-data-jpa` and `spring-boot-starter-validation` are declared
- AND `runtimeOnly 'org.postgresql:postgresql'` is declared
- AND the content contains no `io.spring.dependency-management`, no `springdoc-openapi-starter-webmvc-ui` and no `actuator`

(Previously: "AND the content contains no `springdoc` and no `io.spring.dependency-management`".)

#### Scenario: build.gradle declares the springdoc API starter at the single-sourced version

- GIVEN `SPRINGDOC_VERSION` in `emit/versions.py`
- WHEN `build.gradle` is generated and the emit package sources and templates are scanned
- THEN it contains `implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:` followed by exactly that version
- AND the literal `3.1.1` appears in `emit/versions.py` only, in no other emit module or template (DD72 scan)

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

- GIVEN the pinned Spring Boot, Java and springdoc versions declared in the single versions module
- WHEN the scaffold is generated and the emit package sources are inspected
- THEN the Boot version in `build.gradle` equals the module's Boot value, the toolchain version equals its Java value, and the springdoc version equals its springdoc value
- AND each pinned version literal is defined in that module only, not in the renderer, templates or other emit modules

#### Scenario: Invalid base package is rejected without output

- GIVEN a `base_package` that fails the existing validation (for example `Com.Example`, `com-example`, `com..example`, an empty string, or a Java-invalid leading digit segment)
- WHEN `generate_project_scaffold_sources` is invoked
- THEN it raises the same error the existing base-package validation raises for the other entry points
- AND no `GeneratedSources` is returned
