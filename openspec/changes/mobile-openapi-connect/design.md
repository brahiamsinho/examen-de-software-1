# Design: Mobile manual connection to a generated API

## Layout (`mobile/lib/features/api_connection/`)

| Layer | File | Responsibility |
|---|---|---|
| domain | `openapi_url.dart` | `normalizeOpenApiUrl(String) -> Uri`, throws `ConnectionFailure.invalidUrl` |
| domain | `connection_failure.dart` | `ConnectionFailureKind` enum + `ConnectionFailure` (kind, detail, statusCode) implements `Exception` |
| domain | `api_discovery.dart` | `ApiDiscovery`, `EndpointGroup`, `ApiEndpoint` (immutable) |
| data | `openapi_parser.dart` | pure `parseOpenApi(Object? json) -> ApiDiscovery` |
| data | `openapi_client.dart` | `OpenApiClient({http.Client?, Duration timeout})`, `fetch(Uri)` |
| presentation | `connect_controller.dart` | `ChangeNotifier`, sealed `ConnectState` |
| presentation | `connect_page.dart`, `discovery_page.dart` | screens |

Also: `lib/app.dart` (`ModeliaApp({OpenApiClient? client})`), `lib/main.dart`, `core/config/app_config.dart`.

## Decisions

- **D1 http package only.** `MockClient` gives network-free tests; no state-management package: `ChangeNotifier` + sealed states + `ListenableBuilder` is enough for one screen.
- **D2 Failures as exceptions in data, states in presentation.** Client and parser throw `ConnectionFailure`; the controller catches it into `ConnectState.failure`. Any other exception from the client is mapped to `network`.
- **D3 Keep the path prefix.** Deployments live behind `/gen/<id>/`; dropping the path would never connect. Query/fragment/userinfo are dropped.
- **D4 Grouping.** Group by first tag; no tag -> segment after `api`, else first segment, else `untagged`. Root `tags[].description` is not used in stage 1.
- **D5 No `dart:io` import** in lib code so `web/` keeps compiling; socket errors are caught as generic `Exception` -> `network`.
- **D6 Stale response guard.** Controller keeps a request counter; only the latest request may set state. A second `connect` while loading is ignored.
- **D7 Timeout default 10 s**, constructor parameter (tests use milliseconds). Not an env define (YAGNI).
- **D8 Android.** `INTERNET` in `main` manifest (release needs it); `android:usesCleartextTraffic="true"` only in `src/debug/AndroidManifest.xml` for LAN IP over http. Production expects HTTPS (Caddy).
- **D9 English UI copy and identifiers** per project convention.

## Flow

User text -> `ConnectController.connect` -> `normalizeOpenApiUrl` -> `OpenApiClient.fetch` (GET, `Accept: application/json`, timeout) -> `jsonDecode` -> `parseOpenApi` -> `ConnectState.success` -> `ConnectPage` pushes `DiscoveryPage` -> controller resets on return.

## Testing (Strict TDD, `flutter_test`)

1. `openapi_url_test`: table of valid/invalid inputs.
2. `openapi_parser_test`: valid 3.0/3.1, swagger 2, no `paths`, non-map, untagged grouping, sorting.
3. `openapi_client_test` with `MockClient`: 200, 404, HTML body, timeout, thrown error.
4. `connect_controller_test`: idle -> loading -> success/failure, double-submit ignored, stale response ignored.
5. `connect_page_test` (widget): empty/invalid error, loading indicator, failure keeps text, success shows discovery.
