# Proposal: Mobile manual connection to a generated API

## Intent

`mobile/` is still the Flutter counter template. Generated backends already expose `public_url`,
`openapi_url` and `/v3/api-docs`. Stage 1 of the generic Flutter app lets a user type a deployment
URL, download and validate its OpenAPI 3 document, and see what the API exposes. It is the base
that later stages (`mobile-ui.json`, dynamic CRUD, Modelia login) build on.

## Scope

### In Scope
- "Connect to generated API" screen (URL input, loading, error states).
- URL normalization to `<base>/v3/api-docs`, preserving any path prefix (`/gen/<id>`).
- Download + validation of an OpenAPI 3 document (timeout, network, HTTP, JSON, schema errors).
- Discovery screen: API title/version, tags (entities) and their endpoints (method + path).
- Optional `--dart-define=GENERATED_API_URL` to pre-fill the field (no default value).
- Android `INTERNET` permission; cleartext HTTP only in the debug manifest.

### Out of Scope
- Dynamic CRUD forms, `mobile-ui.json`, Modelia login, deployment selector, local AI, Flutter codegen.
- Persisting the URL, authentication headers, OpenAPI 2 / `$ref` resolution.

## Capabilities

### New Capabilities
- `mobile-api-connection`: manual URL normalization, OpenAPI 3 fetch/validation and endpoint discovery in the Flutter app.

### Modified Capabilities
None.

## Approach

Feature module `lib/features/api_connection/{domain,data,presentation}`. Pure domain (URL
normalizer, models, failures), pure parser, thin HTTP client (`package:http`, injectable for
`MockClient`), `ChangeNotifier` controller with sealed states. New dependency: `http` only.
Strict TDD, tests before each unit.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `mobile/lib/features/api_connection/` | New | domain, data, presentation |
| `mobile/lib/main.dart` | Modified | template replaced by `ModeliaApp` |
| `mobile/lib/core/config/app_config.dart` | Modified | `GENERATED_API_URL` |
| `mobile/pubspec.yaml` | Modified | `http` |
| `mobile/test/` | Modified/New | template test replaced |
| `mobile/android/app/src/{main,debug}/AndroidManifest.xml` | Modified | permissions |
| `docs/ai/*` | Modified | CURRENT_STATE, HANDOFF_LATEST, NEXT_STEPS, session note |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Flutter SDK not on PATH: tests cannot run | High | Ask user for SDK path before `apply`. |
| Cleartext HTTP blocked on Android 9+ with a LAN IP | Med | `usesCleartextTraffic` in debug manifest only. |
| Springdoc documents may be large | Low | Parse once; no `$ref` resolution. |

## Rollback Plan

Everything is under `mobile/` and `docs/ai/`; `git revert` the commit or restore `mobile/`
(no backend, frontend, Docker or DB changes).

## Dependencies

- Flutter SDK (^3.12) usable from the shell.
- A running generated backend for a manual smoke check (optional).

## Success Criteria

- [ ] Valid `/gen/<id>` or `/v3/api-docs` URL leads to a discovery screen listing tags and endpoints.
- [ ] Invalid URL, timeout, network error, non-200, non-JSON and non-OpenAPI-3 each show a distinct message.
- [ ] `flutter test` and `flutter analyze` pass; no URL/IP hardcoded.
