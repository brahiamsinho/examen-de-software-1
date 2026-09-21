# Tasks: mobile-openapi-connect

## Review Workload Forecast

- Estimated changed lines: ~900 (about 400 source, about 500 tests). Chained PRs recommended: Yes. 400-line budget risk: High. Decision needed before apply: Yes.
- Natural slices: (A) domain + parser + client (tasks 1-4), (B) controller + UI + app wiring + Android + docs (tasks 5-8).

## 1. Setup
- [ ] 1.1 Add `http` to `mobile/pubspec.yaml`, run `flutter pub get`.
- [ ] 1.2 Delete the counter test in `mobile/test/widget_test.dart` (replaced by task 6).

## 2. URL normalization (domain)
- [ ] 2.1 RED `test/features/api_connection/domain/openapi_url_test.dart` (spec: URL Normalization scenarios + edge cases: whitespace, uppercase scheme, port, IPv4, query/fragment, `swagger-ui.html`, prefix, trailing slash, `ftp://`, empty).
- [ ] 2.2 GREEN `connection_failure.dart` + `openapi_url.dart`.

## 3. Discovery models and parser (data)
- [ ] 3.1 RED `openapi_parser_test.dart` (spec: Validation + Discovery scenarios; 3.0 and 3.1, swagger 2, missing/invalid `paths`, non-map, untagged, sort order, non-method keys like `parameters` ignored).
- [ ] 3.2 GREEN `api_discovery.dart` + `openapi_parser.dart`.

## 4. HTTP client (data)
- [ ] 4.1 RED `openapi_client_test.dart` with `MockClient` (200, 404, HTML, timeout, thrown exception).
- [ ] 4.2 GREEN `openapi_client.dart`.

## 5. Controller (presentation)
- [ ] 5.1 RED `connect_controller_test.dart` (transitions, invalid URL never hits client, double submit ignored, stale response ignored, reset).
- [ ] 5.2 GREEN `connect_controller.dart`.

## 6. UI and wiring
- [ ] 6.1 RED `connect_page_test.dart` (spec: Connection Flow scenarios; pre-fill from a passed initial URL).
- [ ] 6.2 GREEN `connect_page.dart`, `discovery_page.dart`, `app.dart`, `main.dart`, `app_config.dart` (`GENERATED_API_URL`).

## 7. Android
- [ ] 7.1 `INTERNET` in main manifest; cleartext only in debug manifest (verify current manifests first).

## 8. Verify and docs
- [ ] 8.1 `flutter analyze` and `flutter test` green.
- [ ] 8.2 Manual smoke against a real deployment (`/gen/<id>`), if one is running.
- [ ] 8.3 Update `docs/ai/CURRENT_STATE.md`, `HANDOFF_LATEST.md`, `NEXT_STEPS.md`; add `docs/ai/sessions/2026-09-21-mobile-openapi-connect.md`; DECISIONS_LOG entry for D3/D8.
