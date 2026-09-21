# Mobile API Connection Specification

## Purpose

The Flutter app connects manually to a generated backend by URL, validates its OpenAPI 3
document and shows what the API exposes.

## Requirements

### Requirement: URL Normalization

The app MUST turn user input into the OpenAPI document URL `<origin>[/prefix]/v3/api-docs`.
Input MUST be trimmed, MUST use scheme `http` or `https` with a non-empty host, and query and
fragment MUST be dropped. A path prefix MUST be preserved. A URL already ending in
`/v3/api-docs` MUST be kept as is; one ending in `/swagger-ui/index.html` or
`/swagger-ui.html` MUST have that suffix replaced; otherwise `/v3/api-docs` MUST be appended.
Empty input or an unsupported scheme MUST be rejected as an invalid URL.

#### Scenario: Deployment URL with prefix
- GIVEN the input `https://demo.example.com/gen/abc/`
- WHEN it is normalized
- THEN the result is `https://demo.example.com/gen/abc/v3/api-docs`

#### Scenario: Swagger UI URL
- GIVEN the input `http://192.168.1.5:8090/gen/abc/swagger-ui/index.html?x=1`
- WHEN it is normalized
- THEN the result is `http://192.168.1.5:8090/gen/abc/v3/api-docs`

#### Scenario: Invalid input
- GIVEN the input `` (empty), `ftp://host` or `not a url`
- WHEN it is normalized
- THEN an invalid URL failure is produced and no request is made

### Requirement: OpenAPI Document Validation

The app MUST download the normalized URL with an HTTP GET and a bounded timeout, and MUST
accept it only if it is a JSON object whose `openapi` field is a string starting with `3.` and
whose `paths` field is an object. Each failure MUST map to one distinct failure kind: invalid
URL, timeout, network error, HTTP status (with the code), not JSON, invalid OpenAPI (with a reason).

#### Scenario: Valid document
- GIVEN a 200 response with `{"openapi":"3.1.0","info":{...},"paths":{...}}`
- WHEN it is fetched
- THEN a discovery result is produced

#### Scenario: Wrong kinds of failure
- GIVEN respectively a 404, an HTML body, a JSON `{"swagger":"2.0"}`, a request exceeding the timeout, and a socket error
- WHEN each is fetched
- THEN the failures are HTTP status 404, not JSON, invalid OpenAPI, timeout and network error

### Requirement: Endpoint Discovery

The discovery result MUST expose API title, API version, OpenAPI version and endpoints
(HTTP method + path, for `get`, `post`, `put`, `patch`, `delete`) grouped by tag. An endpoint
with no tag MUST be grouped by the segment following `/api/` (or its first segment) and MUST
never be dropped. Groups MUST be sorted by name.

#### Scenario: Tagged endpoints
- GIVEN paths `/api/class-as` (get, post) tagged `class-a-controller` and `/api/class-as/{id}` (get, put, delete) with the same tag
- WHEN discovery is built
- THEN one group `class-a-controller` lists 5 endpoints

#### Scenario: Untagged endpoint
- GIVEN `/api/orders` (get) with no tags
- WHEN discovery is built
- THEN it is listed in group `orders`

### Requirement: Connection Flow and Feedback

The connect screen MUST show a loading state while a request is in flight and MUST ignore
further submissions during it. Failures MUST show a distinct human-readable message and keep
the entered text. Success MUST navigate to the discovery screen.

#### Scenario: Loading
- GIVEN a valid URL is submitted
- WHEN the request is pending
- THEN the button is disabled and a progress indicator is shown

#### Scenario: Failure keeps input
- GIVEN a submission fails with a timeout
- WHEN the result arrives
- THEN the timeout message is shown and the field still holds the URL

### Requirement: Configuration

The app MUST NOT hardcode any backend URL, IP or secret. An optional compile-time
`GENERATED_API_URL` (`--dart-define`) MAY pre-fill the field and MUST default to empty.

#### Scenario: No define
- GIVEN the app runs without `GENERATED_API_URL`
- WHEN the connect screen opens
- THEN the field is empty
