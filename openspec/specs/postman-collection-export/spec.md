# Postman Collection Export Specification

## Purpose

Defines how a captured OpenAPI 3 document (the `/v3/api-docs` body of the generated Spring project) is converted, offline and deterministically, into a Postman Collection v2.1.0 plus an environment file, and the CLI that drives it. Lives in the Django app `apps.postman_export`. Out of scope: auth, id chaining / newman-runnable collection, Domain Manifest, deriving the document from the relational model.

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run. Items marked **(fixture-dependent)** are confirmed against the committed REAL captured document before being pinned.

## Requirements

### Requirement: Pure Deterministic Converter

The converter MUST be a pure function (`dict` in, `dict` out) using only the Python standard library. It MUST NOT generate random ids, MUST NOT emit `_postman_id`, and MUST NOT read the clock or the environment. Two runs on the same input MUST yield equal output; serialized files MUST be byte-identical. **[pytest]**

#### Scenario: Same input, same bytes

- GIVEN the committed real OpenAPI fixture
- WHEN the converter runs twice and each result is serialized by the CLI
- THEN both results are equal and both output files are byte-identical

#### Scenario: No volatile fields

- GIVEN the converted collection
- WHEN it is scanned recursively
- THEN no `_postman_id` key exists and no generated id or timestamp appears

### Requirement: Real Captured Fixture

The first TDD fixture MUST be the REAL `/v3/api-docs` body captured by the gate (trimmed to the Customer controller only if oversized, stated in the test docstring), committed with recorded provenance (springdoc 3.1.1 and capture date). Converter tests MUST be driven by it, not by assumed shapes. **[pytest]**

#### Scenario: Fixture drives the suite

- GIVEN the committed fixture and its provenance note
- WHEN `pytest -q` runs offline
- THEN converter tests load the fixture and pass without Docker, network or a JVM

### Requirement: Collection Envelope

The output MUST be a Postman Collection v2.1.0: `info.schema` equal to `https://schema.getpostman.com/json/collection/v2.1.0/collection.json` and `info.name` equal to the OpenAPI `info.title`. No `auth` block MUST be emitted at collection, folder or request level. **[pytest]**

#### Scenario: Envelope fields

- GIVEN an OpenAPI document with `info.title` "T"
- WHEN it is converted
- THEN `info.name` is "T", `info.schema` is the v2.1.0 URL above, and no `auth` key exists anywhere

### Requirement: Request URL and Naming

Each operation MUST become one request whose URL is `{{baseUrl}}` plus the path, with `{id}` rewritten as the `:id` path variable (declared under `url.variable`). The OpenAPI `servers` array MUST be ignored. The request name MUST be `METHOD path` (e.g. `GET /api/customers/{id}`) and MUST NOT use `operationId`. **[pytest]**

#### Scenario: Path variable and base URL

- GIVEN a `GET /api/customers/{id}` operation and a `servers` entry with a host
- WHEN it is converted
- THEN the raw URL is `{{baseUrl}}/api/customers/:id`, `id` is a path variable, and the servers host appears nowhere

#### Scenario: Name is method plus path

- GIVEN two operations sharing an `operationId`
- WHEN they are converted
- THEN their names are distinct `METHOD path` strings

### Requirement: Folders and Ordering

Requests MUST be grouped in one folder per first operation tag, falling back to folder `default` when the operation has no tags. Folders MUST be sorted, and items within a folder MUST be sorted by (path, method). **[pytest]**

#### Scenario: Tag folder

- GIVEN operations tagged `customer-controller`
- WHEN they are converted
- THEN they appear inside folder `customer-controller`

#### Scenario: Untagged operation and order

- GIVEN an untagged operation and input paths in shuffled order
- WHEN converted
- THEN the untagged request is in folder `default` and folders and items are sorted identically for every input order

### Requirement: Body Example Generation

Requests that have a JSON request body MUST carry a raw JSON example generated from the request schema. The generator MUST resolve `$ref` and handle string, uuid, integer, number, boolean, date-time, enum (first value), array and object, and MUST guard against reference cycles with a depth limit. Generated example values MUST be deterministic. **[pytest]**

#### Scenario: Body from schema

- GIVEN `CustomerRequestDto` with a string `fullName`
- WHEN the POST request is converted
- THEN its body is JSON containing `fullName` with a string value

#### Scenario: Cyclic schema terminates

- GIVEN a schema referencing itself
- WHEN an example is generated
- THEN generation terminates within the depth limit without error

### Requirement: Pageable Expansion

A collection-list GET whose OpenAPI parameters describe a `Pageable` object (a single `pageable` query parameter with an object schema) MUST be expanded into the separate query params `page`, `size` and `sort`. The exact springdoc shape and defaults are **(fixture-dependent)**. **[pytest]**

#### Scenario: Pageable expanded

- GIVEN the fixture's paged list operation
- WHEN it is converted
- THEN its URL query contains `page`, `size` and `sort` and no `pageable` param

### Requirement: Status-Code Test

Each request whose operation documents a numeric 2xx response MUST carry one event of `listen: test` (a request whose operation documents no numeric 2xx carries no test event, DD119) asserting the response status equals the lowest documented 2xx code of its operation. No id chaining (no capturing of ids into variables) MUST be performed. **[pytest]**

#### Scenario: Test per request

- GIVEN a POST documenting 201 and a DELETE documenting 204
- WHEN converted
- THEN each request has exactly one test event asserting its own code (201, 204)

#### Scenario: No chaining

- GIVEN the converted collection
- WHEN scanned
- THEN no test or pre-request script sets collection or environment variables

### Requirement: Environment File

The converter MUST also produce an environment file with a single variable `baseUrl`. Its value MUST come from the optional `--base-url` argument and MUST default to an empty string. No host, port or URL literal MUST exist in the app source. `baseUrl` values MUST appear only in the environment file. **[pytest]**

#### Scenario: Default empty

- GIVEN no `--base-url`
- WHEN the environment file is produced
- THEN `baseUrl` has an empty value

#### Scenario: Value supplied

- GIVEN `--base-url` with a value
- WHEN the environment file is produced
- THEN `baseUrl` carries that value and the collection file does not

#### Scenario: No literals in source

- GIVEN every module of `apps.postman_export`
- WHEN a guard test scans string literals
- THEN none contains a host, port or `http` URL (other than the Postman schema URL)

### Requirement: CLI Contract

`python -m apps.postman_export.cli --openapi <file> --out-dir <dir> [--base-url <value>]` MUST write the fixed-name files `postman_collection.json` and `postman_environment.json` (DD111; the collection `info.name` still comes from the OpenAPI `info.title`) into `--out-dir` (creating it if missing) without calling `django.setup()`. Exit codes MUST be: 0 success; 1 with a message on stderr for an unreadable file, invalid JSON, or an OpenAPI shape the converter cannot handle; 2 for argparse usage errors. **[pytest]**

#### Scenario: Success

- GIVEN the real fixture and a writable `--out-dir`
- WHEN the CLI runs
- THEN it exits 0 and both files exist

#### Scenario: Bad input

- GIVEN a missing file, non-JSON content, or a document with no `paths`
- WHEN the CLI runs
- THEN it exits 1 with a stderr message and writes no output

#### Scenario: Usage error

- GIVEN `--openapi` omitted
- WHEN the CLI runs
- THEN it exits 2

#### Scenario: No Django bootstrap

- GIVEN the CLI runs
- WHEN it completes
- THEN `django.setup` was never called and no `POSTGRES_*` variables were required

### Requirement: App Registration and Decoupling

`apps.postman_export` MUST be registered in INSTALLED_APPS. Its converter and CLI modules MUST NOT import Django or `apps.spring_generator` / `apps.generation_runner`, and no other app MUST import `apps.postman_export`. A guard test MUST enforce this. **[pytest]**

#### Scenario: Import guard

- GIVEN every module in the converter and CLI
- WHEN a guard test scans imports
- THEN none references `django` or the generator apps, and the app is present in INSTALLED_APPS
