```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:eee48ccd5da76f4784a9778ae29e9547122598fe000000000000000000000000
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 6/6
scenarios: 10/10
test_command: docker compose exec backend pytest apps/uml_documents -q
test_exit_code: 0
test_output_hash: sha256:fed24f101aa498672c0ca8265702d1b7f50ba2ccb9d7c331e4b6903dc9aa8920
build_command: docker compose exec backend pytest -q
build_exit_code: 0
build_output_hash: sha256:3613df2e7034d7f2c62c982446e1bdf7d232d4bf00c9befabd821a4ffd5ff345
```

## Verification Report

**Change**: uml-document-persistence
**Version**: N/A (first cycle for this capability)
**Mode**: Strict TDD
**HEAD at verification time**: eee48ccd5da76f4784a9778ae29e9547122598fe (branch feature/uml-document-persistence, uncommitted working tree changes under backend/apps/uml_documents/, backend/config/settings.py, backend/config/api.py, openspec/changes/uml-document-persistence/)

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 30 |
| Tasks complete | 30 |
| Tasks incomplete | 0 |

All 30 tasks across Phases 1-8 in tasks.md are checked [x]. Cross-checked against actual files present in backend/apps/uml_documents/ -- every file named in every task exists with the described behavior (verified by direct source read of every production and test file, not just the checkbox or the apply-progress narrative).

### Mid-Apply Spec/Design Correction -- Scrutinized and Confirmed Sound

The original spec.md Import Boundary requirement omitted apps.organizations from the allowed-imports list, directly contradicting the Tenant Scoping requirement in the same document (which mandates TenantScopedModel/TenantScopedManager/resolve_membership/require_role/Role, all of which live only in apps.organizations). This was caught by test_import_boundary.py failing on models.py's necessary TenantScopedModel import, and fixed by the orchestrator across spec.md, design.md, tasks.md (task 6.1 wording), and the test file itself.

Independently re-verified in this session, not merely re-read:
- spec.md, design.md, tasks.md, and test_import_boundary.py all state the identical corrected rule: apps.organizations allowed, apps.users forbidden, api.py excluded from the scoped file set. No drift between the four artifacts.
- Confirmed apps.users is imported nowhere under backend/apps/uml_documents/ except in one code comment string and the test's own _DISALLOWED_PREFIXES literal (a grep for apps.users over the whole app directory returns only test_import_boundary.py and conftest.py's docstring prose -- no actual "import apps.users" statement anywhere in models.py/codec.py/services.py/schemas.py/api.py).
- Confirmed the corrected test is NOT "allow everything" laundered as a fix: simulated adding "import apps.users" to services.py's source and re-ran the exact _ALLOWED_PREFIXES/_DISALLOWED_PREFIXES logic against the mutated AST -- the simulated import fails both the allow-list assertion and the disallow-list assertion, confirming the test still catches a real violation.
- Confirmed apps.organizations is a narrow, justified addition (TenantScopedModel, TenantScopedManager in models.py; Organization in services.py; Role/require_role/resolve_membership in api.py, which is outside the AST-scoped file set) -- not an unbounded widening of the boundary.

This correction is coherent, consistently applied, and not a defect.

### Build & Tests Execution

**Build**: N/A -- no build/compile/bundle step this cycle (pure Python/Django app, no new external dependency; one new migration, applied cleanly against the test DB as part of every @pytest.mark.django_db test run).

**Tests (scoped)**: PASS 33 passed / FAIL 0 / SKIP 0

    $ docker compose exec backend pytest apps/uml_documents -q
    .................................                                        [100%]
    33 passed in 7.99s

**Tests (full-suite regression)**: PASS 309 passed / FAIL 0 / SKIP 0

    $ docker compose exec backend pytest -q
    ........................................................................ [ 23%]
    ........................................................................ [ 46%]
    ........................................................................ [ 69%]
    ........................................................................ [ 93%]
    .....................                                                    [100%]
    309 passed in 35.60s

Both commands were re-run independently, twice, in this verify session (not copied from apply-progress claims). Zero regressions against the pre-existing 276-test suite from the prior uml-command-bus cycle plus this cycle's own 33.

**Coverage**: Not available -- no coverage tool (pytest-cov) configured in this project. Informational only per strict-TDD rules.

### Zero-Diff Confirmation (independent)

    $ git diff --stat -- backend/apps/uml_modeling backend/apps/uml_commands
    (empty)

    $ git diff -- backend/config/settings.py
    +    "apps.uml_documents",   (1 line added under the Local INSTALLED_APPS marker)

    $ git diff -- backend/config/api.py
    +from apps.uml_documents.api import documents_router   (import)
    +api.add_router("/orgs/{org_slug}/documents", documents_router, tags=["documents"])   (router mount)

Re-run directly in this session, not quoted from the apply report. apps/uml_modeling/ and apps/uml_commands/ are confirmed genuinely untouched; settings.py/api.py carry exactly the minimal lines the design predicted.

### Spec Compliance Matrix (uml-document-persistence -- 6 requirements / 10 scenarios)

| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Document Creation | Editor creates an empty document | test_api.py::TestCreateDocument::test_editor_creates_empty_document; test_services.py::test_create_document | COMPLIANT |
| Document Creation | Viewer is denied creation | test_api.py::TestCreateDocument::test_viewer_is_denied_creation | COMPLIANT |
| Document Read | Any member reads back the persisted document | test_api.py::TestGetDocument::test_any_member_reads_back_the_persisted_document | COMPLIANT |
| Document Read | Cross-tenant read returns 404 | test_api.py::TestGetDocument::test_cross_tenant_read_returns_404; test_integration.py::test_cross_tenant_member_gets_404_on_all_three_endpoints | COMPLIANT |
| Command Submission | Sequential commands persist across calls | test_api.py::TestSubmitCommand::test_sequential_commands_persist_across_calls; test_services.py::test_submit_command; test_integration.py::test_composed_create_add_class_add_attribute_get_round_trip | COMPLIANT |
| Command Submission | Viewer is denied command submission | test_api.py::TestSubmitCommand::test_viewer_is_denied_command_submission | COMPLIANT |
| Command Submission | Invalid result still persists with diagnostics | test_api.py::TestSubmitCommand::test_add_relationship_with_nonexistent_target_returns_violations; test_services.py::test_submit_command_persists_invalid_result_with_diagnostics | COMPLIANT |
| Codec Round-Trip Correctness | Non-trivial model and layout round-trip exactly | test_codec.py::test_round_trips_non_trivial_fixture_exactly (plus 3 supporting cases) | COMPLIANT |
| Tenant Scoping on Every Access | A document is unreachable through the requesting members own org only | test_integration.py::test_cross_tenant_member_gets_404_on_all_three_endpoints; test_api.py::test_cross_tenant_read_returns_404 | COMPLIANT |
| uml_documents Import Boundary | uml_modeling and uml_commands have zero diff | test_import_boundary.py::test_no_disallowed_imports_exist; independent git diff --stat re-run | COMPLIANT |

Compliance summary: 10/10 scenarios compliant across 6/6 requirements.

### Correctness -- the 8 flagged scrutiny checks

1. Import Boundary correction coherence. CONFIRMED -- see dedicated section above. The correction is consistent across all 4 artifacts, apps.users is genuinely imported nowhere in scoped or unscoped production files, and the test provably still fails on a simulated real violation.

2. Codec lossless round-trip on a genuinely non-trivial fixture. CONFIRMED. tests/factories.py a_model() builds 2 classes, 1 enumeration (2 literals), 1 relationship, and a non-empty generation_metadata dict keyed by real ElementIds with nested dict values; both AttributeType branches (PrimitiveType.STRING and EnumerationRef) are exercised across the two classes attributes. a_layout(model) builds non-empty positions keyed by the same class ids. test_codec.py test_round_trips_non_trivial_fixture_exactly asserts full dataclass equality on metadata, model, and layout after a to_json/from_json round trip -- not a partial/shallow check. Additional tests separately confirm generation_metadata key/value fidelity, both AttributeType branches, and empty-collection round-trip.

3. UmlDocument.objects is the raising TenantScopedManager; services.py never bypasses it. CONFIRMED. apps.organizations.models.TenantScopedManager.get_queryset() raises TenantScopeViolation unless accessed through an instance reverse relation; .for_organization(org) explicitly calls .unscoped().filter(organization=org) to bypass the raise deliberately and safely. Grepped services.py for objects.get(/objects.filter(/objects.create( -- the only occurrence of the string all_objects in that file is inside a docstring comment; every actual lookup/creation goes through UmlDocument.objects.for_organization(organization).get(...) or .create(...). test_models.py test_uml_document_managers independently asserts UmlDocument.objects is a TenantScopedManager and all_objects is a plain Manager.

4. submit_command never gates persistence on validation_result.is_blocking. CONFIRMED by source and by test. services.submit_command calls apply(...) then unconditionally calls _save(row, result.document) -- no branch inspects result.validation_result before saving. test_services.py test_submit_command_persists_invalid_result_with_diagnostics submits AddRelationship with a nonexistent target class id and asserts result.validation_result.is_blocking is True, INVALID_RELATIONSHIP_ENDPOINT is in the diagnostic codes, AND the persisted document (re-fetched via get_document) matches the returned revision and now contains the relationship. test_api.py test_add_relationship_with_nonexistent_target_returns_violations proves the same at the HTTP layer: response is 200 (not an error status), revision equals 3, and violations include the code.

5. Cross-tenant isolation returns 404, not 403 or leaked content, on all applicable endpoints. CONFIRMED. test_api.py test_cross_tenant_read_returns_404 and test_integration.py test_cross_tenant_member_gets_404_on_all_three_endpoints both assert 404 for GET and POST .../commands across organizations, and the latter additionally asserts the underlying row (UmlDocument.all_objects.get(id=doc_id)) is untouched at revision equals 1 after the cross-tenant command attempt -- proving no side effect leaked through the 404. Note: the spec scenario phrase "any of the three endpoints" is imprecise -- POST /documents (create) has no existing doc_id to leak, so cross-tenant isolation is only a meaningful check for the 2 endpoints that take a doc_id (GET, POST .../commands), both of which are tested. This is a minor spec-wording imprecision, not a functional gap (see SUGGESTION 2 below).

6. Permission checks: POST /documents and POST .../commands require EDITOR/OWNER; GET allows any member. CONFIRMED. api.py create_document_view and submit_command_view both call require_role(membership, Role.OWNER, Role.EDITOR) before any service call; get_document_view calls only resolve_membership, no role check. test_api.py test_viewer_is_denied_creation and test_viewer_is_denied_command_submission both assert 403 and assert the document is not created/not modified (UmlDocument.all_objects query). test_any_member_reads_back_the_persisted_document proves a VIEWER can GET.

7. Discriminated-union CommandIn works for all 7 types; malformed/unknown type produces 422, not a crash. CONFIRMED for the outer discriminator by both a static test and a live ad-hoc empirical check run in this session (not shipped as a permanent test -- see WARNING 1 below for the related gap this surfaced). test_schemas.py test_command_in_discriminates_each_of_the_seven_shapes parametrizes all 7 type-tagged shapes via pydantic.TypeAdapter(CommandIn).validate_python(...) and asserts the correct sub-schema class is produced for each. A live HTTP POST with an unknown type value against a real running instance (via a temporary throwaway test added and removed within this session; final suite count unaffected, still exactly 33 passed after removal) returned HTTP 422 with a clean pydantic union_tag_invalid error body naming all 7 valid tags -- proving django-ninja built-in body-validation exception handling covers the outer discriminator correctly, with no custom code required and no crash.

   However, the same live empirical check performed on an inner malformed shape (a well-formed outer AddAttribute envelope carrying a malformed attribute.type value, e.g. a dict without an enumeration_ref key, instead of a PrimitiveType string or a well-formed enumeration_ref dict) reproduced an unhandled KeyError propagating to a genuine HTTP 500 Internal Server Error -- traced to codec.py _decode_attribute_type (line 229) being called from services.py _attribute_from_schema (line 119) from services.py command_from_payload (line 102), with no try/except anywhere on that path and no ninja/Django exception handler registered for it. This is flagged as WARNING 1 below -- it is a real, reachable, currently-untested 500 path reachable by any authenticated EDITOR, not merely a hypothetical.

8. apps/uml_modeling/ and apps/uml_commands/ are genuinely untouched. CONFIRMED independently. git diff --stat -- backend/apps/uml_modeling backend/apps/uml_commands produced empty output, re-run directly in this session, not quoted from the apply report.

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| DD1 New sibling app uml_documents, depends on uml_modeling/uml_commands/organizations | Yes | Confirmed via import-boundary test and direct read of every production file imports. |
| DD2 One generic POST .../commands endpoint, Body[CommandIn] discriminated union | Yes | api.py submit_command_view; schemas.py CommandIn -- Annotated Union of the 7 schemas with Field(discriminator="type"), exactly as designed. |
| DD3 UmlDocument: real columns id/owner_id/revision/timestamps; data blob holds only metadata+model+layout | Yes | models.py matches the Interfaces/Contracts block field-for-field. |
| DD4 created_at/updated_at plain DateTimeField, set explicitly from injected now | Yes | No auto_now/auto_now_add anywhere in models.py; services.py create_document/_save both take/use an explicit now/document.updated_at. |
| DD5 codec.to_json(metadata, model, layout)/from_json(data) returns a tuple -- content-triple only | Yes | Exact signature match; services.py is the sole place assembling a full ProjectDocument. |
| DD6 ElementId-keyed mappings encode with no key stringify | Yes | _encode_model/_decode_model, _encode_layout/_decode_layout confirmed -- ElementId(k) re-wrap on decode is a no-op at runtime, confirmed by the round-trip test passing exactly. |
| DD7 AttributeType encodes as plain string (PrimitiveType) or tagged enumeration_ref dict (EnumerationRef) | Yes | _encode_attribute_type/_decode_attribute_type match design exactly; both branches round-trip-tested. See WARNING 1 for the malformed-input side of this same function. |
| DD8 Schema-to-domain conversion lives in services.command_from_payload, not api.py/schemas.py | Yes | api.py handlers stay thin; schemas.py has zero methods; all 7-way dispatch and nested conversion (_attribute_from_schema, _relationship_from_schema) live in services.py. |
| DD9 POST /documents and POST .../commands require OWNER/EDITOR; GET requires no role check | Yes | Confirmed in api.py and by test (require_role call present/absent as designed). |

All 9 design decisions are followed in the actual code, no deviations found.

### TDD Compliance

| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | Yes | tasks.md documents RED-then-GREEN per task inline across all 8 phases; apply-progress (Engram obs 523) confirms all 30 tasks complete. |
| All tasks have tests | Yes | 30/30 tasks map to a real test file or are explicitly structural/no-new-code phases (1.1 skeleton, 7.2/8.x confirmation-only, matching tasks.md own wording). |
| RED confirmed (tests exist) | Yes | Every test file named across tasks.md 8 phases exists on disk and was read directly in this session: test_apps.py, test_models.py, test_codec.py, test_services.py, test_schemas.py, test_api.py, test_import_boundary.py, test_integration.py. |
| GREEN confirmed (tests pass) | Yes | 33/33 passed on independent re-run in this verify session; 309/309 full-suite passed, zero regressions. |
| Triangulation adequate | Yes | Multiple test cases per behavior throughout (create/get/cross-tenant, sequential-command revision increments, both AttributeType branches, empty plus non-trivial codec fixtures). |
| Safety Net for modified files | N/A | This cycle creates only new files under a new app plus 3 additive lines in settings.py/api.py; no existing uml_commands/uml_modeling file was modified after being test-covered. |

TDD Compliance: 5/6 checks fully passed, 1 N/A.

### Test Layer Distribution

| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 27 | 5 (test_models.py, test_codec.py, test_services.py, test_schemas.py, test_apps.py) | pytest |
| Integration/API | 4 | 1 (test_api.py) | pytest and Django test client |
| Structural | 1 | 1 (test_import_boundary.py) | pytest and ast |
| E2E (composed) | 2 | 1 (test_integration.py) | pytest and Django test client |
| Total | 33 | 8 test modules | |

Note: the 33 total above is the exact pytest apps/uml_documents -q count; the per-layer breakdown is derived by classifying test function bodies (HTTP client vs. direct service/model calls), not from a separate tool.

### Changed File Coverage

Coverage analysis skipped -- no coverage tool (pytest-cov) detected in backend/pyproject.toml or installed in the container. Not a failure; informational only per strict-TDD rules. As a proxy, every production module has a directly corresponding test module (models.py to test_models.py, codec.py to test_codec.py, services.py to test_services.py, schemas.py to test_schemas.py, api.py to test_api.py), confirmed by 1:1 file-name mapping and by reading each pair, plus test_integration.py exercising all 3 endpoints together end-to-end.

### Assertion Quality

Audited all 8 test modules plus factories.py/conftest.py.

- No tautologies found.
- No smoke-test-only patterns; every test asserts specific resulting values (revision numbers, class/attribute counts, diagnostic codes, 404/403/200/201 status codes, object identity for tenant isolation via UmlDocument.all_objects).
- No implementation-detail coupling beyond what the design explicitly documents (e.g. tests legitimately reach into UmlDocument.all_objects to cross-check persisted state bypassing the API, matching the pattern used by the prior uml-command-bus cycle own tests).
- test_apps.py single structural assertion is justified (no branching logic to triangulate, matches sibling apps own precedent).

Assertion quality: All assertions verify real behavior.

### Quality Metrics

Linter: Not available, no linter configuration detected for this run.
Type Checker: Not available, no mypy/pyright run performed in this verification session.

### Issues Found

CRITICAL: None

WARNING:

1. Malformed inner command-payload shapes crash with an unhandled HTTP 500 instead of a clean 4xx, and there is zero test coverage of this path. Empirically reproduced in this verify session: POST /orgs/{slug}/documents/{doc_id}/commands with a well-formed outer envelope (type AddAttribute, class_id c1, attribute id a1 name bad type set to a dict without an enumeration_ref key) raises an unhandled KeyError enumeration_ref inside codec.py _decode_attribute_type (line 229), called from services.py _attribute_from_schema (line 119) from services.py command_from_payload (line 102). No try/except exists anywhere on this call path, and no ninja/Django exception handler is registered for it, so the response is a genuine Django 500 (confirmed via the ninja/Django traceback, not inferred). The same class of gap applies to parse_multiplicity (called from _relationship_end_from_schema) and any other inner shape not covered by pydantic own field types (UmlAttributeIn.type is typed str or dict, RelationshipEndIn.multiplicity is typed str -- both loosely typed by design; design.md own Open Questions section flagged this as an accepted tradeoff but explicitly said it is flagged in case sdd-verify disagrees). This is a genuinely reachable path for any authenticated EDITOR (not just an admin), not a hypothetical: a malformed nested field in an otherwise well-formed command can crash the server with a 500 today.

   Exact remediation: in backend/apps/uml_documents/services.py, wrap the inner conversion calls in command_from_payload (_attribute_from_schema, _relationship_from_schema, and by extension codec._decode_attribute_type/parse_multiplicity) to catch KeyError/ValueError/TypeError and re-raise as a request-level validation error (for example ninja.errors.ValidationError, or a small dedicated exception mapped to 422 via api.add_exception_handler, mirroring the existing register_organization_exception_handlers pattern in apps/organizations/api.py); add at least two covering tests in test_api.py -- a malformed attribute.type (e.g. a dict without the enumeration_ref key) and a malformed multiplicity string (e.g. a nonsense string value) -- both asserting 422, not 500, and asserting the document is left unmodified at its prior revision.

SUGGESTION:

1. DiagnosticOut omits element_ref (only severity/code/message/path). None of the 10 spec scenarios require it in the response, and design.md own Open Questions section already flags this explicitly as flagged in case sdd-verify disagrees. Not a defect; carried forward as a documented, accepted scope limitation for this cycle. No remediation required unless a future consumer needs element_ref in the API response.
2. The Tenant Scoping requirement scenario text (any of the three endpoints) is imprecise: cross-tenant isolation is only a meaningful check for the 2 endpoints that take an existing doc_id (GET, POST .../commands) -- POST /documents (create) has no existing document to leak across tenants. The actual behavior is correctly implemented and fully tested for both applicable endpoints (test_cross_tenant_read_returns_404, test_cross_tenant_member_gets_404_on_all_three_endpoints). No code or test change needed; optional future wording fix: reword the scenario to say both id-addressed endpoints instead of any of the three endpoints for precision.
3. No coverage tool is configured for backend/; adding pytest-cov in a future cycle would let subsequent sdd-verify passes report quantitative changed-file coverage instead of relying on file-pairing inspection (same suggestion carried over from the prior uml-command-bus verify report, still unaddressed).

### Verdict

**PASS WITH WARNINGS** (original) — see Post-verify amendment below.

All 30/30 tasks are genuinely complete (verified by source inspection of every production and test file, not just checkboxes). All 10/10 spec scenarios across the 6/6 requirements in uml-document-persistence are covered by tests re-run independently in this session and passed (33/33 scoped, 309/309 full-suite, 0 regressions). All 9 design decisions (DD1-DD9) are followed in the actual code. The mid-apply spec/design correction to the Import Boundary requirement was independently re-verified as coherent, non-contradictory, consistently applied across all 4 artifacts, and still catches a genuine simulated violation -- not a laundered allow-everything change. All 8 specifically flagged scrutiny checks were CONFIRMED against actual source and live empirical HTTP behavior (not assumed from the apply report), including two live ad-hoc requests run against a real Django test client in this session (outer malformed-discriminator returns a clean 422; inner malformed nested shape returns an unhandled 500). The single WARNING is a genuine, empirically-reproduced, currently-untested 500-on-malformed-input path in the command-submission endpoint inner (non-discriminator) payload shapes -- reachable by any authenticated EDITOR, not a hypothetical, and not covered by any existing test. 0 CRITICAL findings. Per this project convention, the WARNING must be remediated (exact fix specified above) before archiving.

### Post-verify amendment

The single WARNING is fixed, exactly per the specified remediation:

- Created `backend/apps/uml_documents/errors.py` — `InvalidCommandPayloadError(ValueError)`.
- `services.py::command_from_payload` now wraps its inner conversion (`_command_from_payload`) in a `try/except (KeyError, ValueError, TypeError)` and re-raises as `InvalidCommandPayloadError`, so a malformed `attribute.type` or `multiplicity` string can no longer reach an unhandled crash.
- `api.py` gained `register_exception_handlers(api)` mapping `InvalidCommandPayloadError` to a clean `422` with `{"detail": ..., "code": "invalid_command_payload"}`, mirroring `apps/organizations/api.py`'s existing exception-handler pattern. Wired into `backend/config/api.py` alongside the existing user/organization handler registrations.
- Added `errors.py` to `test_import_boundary.py`'s scoped file set (zero imports today, but now structurally guarded against future drift).
- Added 2 covering tests to `test_api.py`: `test_malformed_attribute_type_returns_422_not_500` and `test_malformed_multiplicity_returns_422_not_500` — both assert `422` with `code == "invalid_command_payload"`, and that the document's persisted revision is unchanged from before the malformed request (no partial/corrupted mutation).

Re-run independently after the fix: `docker compose exec backend pytest apps/uml_documents -q` → **35 passed** (was 33; +2 new). `docker compose exec backend pytest -q` → **311 passed, 0 regressions** (was 309). `git diff --stat -- backend/apps/uml_modeling backend/apps/uml_commands` → still empty.

**Final Verdict: PASS** (0 CRITICAL, 0 WARNING, 3 non-blocking SUGGESTION carried forward — `element_ref` omission, scenario wording precision, and coverage tooling, all out of scope for this change per project convention).
