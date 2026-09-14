# Archive Report: uml-document-persistence

**Change**: uml-document-persistence
**Archived**: 2026-09-12
**Status**: Complete — Ready for next SDD cycle

## Artifact Traceability

| Artifact | Type | Source | Status |
|----------|------|--------|--------|
| Proposal | filesystem | `openspec/changes/uml-document-persistence/proposal.md` (hybrid mode; no matching `sdd/uml-document-persistence/proposal` Engram observation found — read directly from filesystem) | Retrieved, 2 open product questions flagged for spec/design with stated working assumptions, both later confirmed correct |
| Specification | architecture | Engram #520 (`sdd/uml-document-persistence/spec`) + filesystem `openspec/changes/uml-document-persistence/specs/uml-document-persistence/spec.md` (identical content) | Retrieved, 1 new domain (uml-document-persistence), 6 requirements / 10 scenarios merged |
| Design | filesystem | `openspec/changes/uml-document-persistence/design.md` (hybrid mode; no matching Engram observation found — read directly from filesystem; also independently reconstructed via verify-report's Coherence table, DD1-DD9) | 9 ADRs (DD1-DD9), all followed in code per verify-report |
| Tasks | filesystem | `openspec/changes/uml-document-persistence/tasks.md` (hybrid mode; no matching Engram observation found — read directly from filesystem) | Retrieved, 30/30 tasks completed and checked `[x]` across Phases 1-8 |
| Verify Report | filesystem | `openspec/changes/uml-document-persistence/verify-report.md` (hybrid mode; no matching Engram observation found — read directly from filesystem) | Read directly, **Final Verdict: PASS** (0 CRITICAL, 0 WARNING after post-verify amendment, 3 non-blocking SUGGESTION) |
| Apply Progress (TDD evidence, referenced by verify-report) | n/a | Referenced by verify-report as Engram obs #523 (apply-progress) | Referenced only; not independently re-read for this archive |

**Note on artifact store**: this cycle's `proposal`, `design`, and `tasks` were not found under their expected Engram topic keys at archive time (only `spec` — #520 — was present in Engram). Per hybrid mode, the filesystem copies under `openspec/changes/uml-document-persistence/` are authoritative and complete, and all four core artifacts plus the verify report were read directly from there before archiving.

## Final-State Authority — Verdict Reconciliation

`verify-report.md` records two verdicts in sequence within the same file:

1. **Original verdict** (mid-document): PASS WITH WARNINGS — 1 WARNING: malformed inner command-payload shapes (e.g. a malformed `attribute.type` or `multiplicity` string) crashed with an unhandled HTTP 500 instead of a clean 4xx, with zero test coverage of that path.
2. **Post-verify amendment** (same file, final section): the WARNING was fixed — `backend/apps/uml_documents/errors.py` added (`InvalidCommandPayloadError`), `services.py::command_from_payload` now wraps inner conversion in `try/except` and re-raises as that error, `api.py` registers an exception handler mapping it to a clean `422`, and 2 covering tests were added to `test_api.py` asserting `422` (not `500`) with the persisted revision unchanged. Re-run after the fix: scoped suite 35/35 passed (was 33, +2 new), full suite 311/311 passed (was 309), zero regressions, `apps/uml_modeling`/`apps/uml_commands` diff still empty.

Per the Final-State Authority hierarchy, this archive report records the amended final state — **PASS, 0 WARNING** — not the original pre-amendment WARNING snapshot; the amendment is a fact recorded in the same verify-report.md, ranking above the original verdict text it supersedes within that same document. No contradiction from the orchestrator's launch prompt was found against this — the launch prompt's instruction to "read the Post-verify amendment section to confirm before archiving" was followed, and the section corroborates the stated final verdict (0 CRITICAL, 0 WARNING, 3 non-blocking SUGGESTION).

## Verification Status (per verify-report.md, filesystem)

**Final Verdict: PASS** — 0 CRITICAL, 0 WARNING, 3 non-blocking SUGGESTION carried forward (`element_ref` omission in `DiagnosticOut`, minor scenario-wording imprecision on the Tenant Scoping requirement's "any of the three endpoints" phrase, and no `pytest-cov` coverage tool configured — all explicitly out of scope for this change per project convention, and two of the three carried over verbatim from the prior `uml-command-bus` cycle).

### Completeness Confirmed
- **Tasks**: All 30/30 implementation tasks marked `[x]` in tasks.md (Phases 1-8); cross-checked by verify-report against actual files in `backend/apps/uml_documents/` via direct source read of every production and test file (not checkbox-only).
- **Specs**: 1 new domain spec, 6 requirements, 10 scenarios; all 10/10 scenarios compliant, each mapped to a specific passing test.
- **Design**: 9 ADRs (DD1-DD9) documented in design.md; all followed in the actual code per verify-report's Coherence table, no deviations found.
- **Test Evidence** (independently re-run at verify time, then again after the post-verify amendment — not copied from apply-progress claims):
  - Scoped (post-amendment): 35/35 tests pass (`docker compose exec backend pytest apps/uml_documents -q`)
  - Full-suite regression (post-amendment): 311/311 tests pass, 0 regressions
  - Build: N/A — pure Python/Django app, no build/compile/bundle step; one new migration applied cleanly against the test DB as part of every `@pytest.mark.django_db` run.

### Spec Compliance by Domain

| Domain | Requirements | Scenarios | Status |
|--------|--------------|-----------|--------|
| uml-document-persistence | 6 | 10 | PASS |

### Key Decisions Verified (DD1-DD9)

- **DD1**: New sibling app `uml_documents`, depends on `uml_modeling`/`uml_commands`/`organizations` — confirmed via import-boundary test and direct read of every production file's imports.
- **DD2**: One generic `POST .../commands` endpoint, `Body[CommandIn]` discriminated union — confirmed in `api.py`/`schemas.py`, exactly a `Field(discriminator="type")` union of the 7 payload schemas.
- **DD3**: `UmlDocument` real columns `id`/`owner_id`/`revision`/timestamps; `data` blob holds only metadata+model+layout — confirmed field-for-field against `models.py`.
- **DD4**: `created_at`/`updated_at` are plain `DateTimeField`, set explicitly from an injected `now` — confirmed, no `auto_now`/`auto_now_add` anywhere.
- **DD5**: `codec.to_json(metadata, model, layout)`/`from_json(data)` returns a content-triple tuple only — confirmed exact signature match.
- **DD6**: `ElementId`-keyed mappings encode with no key stringify — confirmed, round-trip test passes exactly.
- **DD7**: `AttributeType` encodes as a plain string (`PrimitiveType`) or a tagged `enumeration_ref` dict (`EnumerationRef`) — confirmed, both branches round-trip-tested.
- **DD8**: Schema-to-domain conversion lives in `services.command_from_payload`, not `api.py`/`schemas.py` — confirmed, API handlers stay thin.
- **DD9**: `POST /documents` and `POST .../commands` require `OWNER`/`EDITOR`; `GET` requires no role check — confirmed in `api.py` and by test.

### Mid-Apply Spec/Design Correction (noteworthy timeline item #1)

The original `spec.md` Import Boundary requirement omitted `apps.organizations` from the allowed-imports list, directly contradicting the Tenant Scoping requirement in the same document (which mandates `TenantScopedModel`/`TenantScopedManager`/`resolve_membership`/`require_role`/`Role`, all of which live only in `apps.organizations`). This was caught during apply by `test_import_boundary.py` failing on `models.py`'s necessary `TenantScopedModel` import, and fixed by the orchestrator across `spec.md`, `design.md`, `tasks.md` (task 6.1 wording), and the test file itself. Verify-report independently re-scrutinized this correction (not merely re-read it) and confirmed: all four artifacts state the identical corrected rule; `apps.users` is genuinely imported nowhere in production code (only in a comment string and the test's own disallow-list literal); a simulated re-introduction of an `apps.users` import still fails both the allow-list and disallow-list assertions, proving the test is not "allow everything" laundered as a fix; and the `apps.organizations` addition is narrow and justified, not an unbounded widening of the boundary. Confirmed coherent, consistently applied, and not a defect.

### Post-Verify Warning Fix (noteworthy timeline item #2)

Verify-report's scrutiny of flagged item 7 (discriminated-union schema validation) empirically reproduced a real, reachable defect: a well-formed outer command envelope carrying a malformed inner field (e.g. `attribute.type` as a dict without an `enumeration_ref` key) crashed with an unhandled `KeyError` propagating to a genuine HTTP 500, traced to `codec.py::_decode_attribute_type` via `services.py::_attribute_from_schema`/`command_from_payload`, with no exception handling anywhere on that path. This was recorded as the single WARNING blocking archive per project convention. It was then fixed exactly per the verify-report's specified remediation (see Verdict Reconciliation above) and re-verified independently in the same verify session: 35/35 scoped tests pass (+2 new covering the malformed-payload cases), 311/311 full-suite tests pass (0 regressions), and `apps/uml_modeling`/`apps/uml_commands` still show zero diff. This closes the gap between the original PASS WITH WARNINGS verdict and the final PASS verdict this archive records.

### Issues Found and Resolution Status

**CRITICAL**: None

**WARNING** (1, resolved before archive):
- Original finding: malformed inner command-payload shapes (a malformed `attribute.type` or `multiplicity` value inside an otherwise well-formed envelope) crashed with an unhandled HTTP 500, with zero test coverage of the path — a genuinely reachable defect for any authenticated `EDITOR`, empirically reproduced during verification, not hypothetical.
- Resolution: `backend/apps/uml_documents/errors.py` added (`InvalidCommandPayloadError`); `services.py::command_from_payload` wraps inner conversion in `try/except (KeyError, ValueError, TypeError)` and re-raises as that error; `api.py` registers an exception handler mapping it to a clean `422` with `{"detail": ..., "code": "invalid_command_payload"}`, mirroring `apps/organizations/api.py`'s existing pattern; `errors.py` added to the import-boundary test's scoped file set; 2 new covering tests added to `test_api.py`, both asserting `422` (not `500`) and an unchanged persisted revision.
- Status: RESOLVED — verify-report.md's own "Post-verify amendment" section confirms the fix and re-run test evidence (35/35 scoped, 311/311 full-suite, 0 regressions).

**SUGGESTIONS** (3, all non-blocking, carried forward, no action needed):
1. `DiagnosticOut` omits `element_ref` (only `severity`/`code`/`message`/`path`). None of the 10 spec scenarios require it in the response; design.md's own Open Questions section already flags this as an accepted scope limitation. No remediation required unless a future consumer needs `element_ref` in the API response.
2. The Tenant Scoping requirement's scenario text ("any of the three endpoints") is imprecise: cross-tenant isolation is only a meaningful check for the 2 endpoints that take an existing `doc_id` (`GET`, `POST .../commands`) — `POST /documents` (create) has no existing document to leak across tenants. The actual behavior is correctly implemented and fully tested for both applicable endpoints. No code or test change needed; optional future wording fix noted.
3. No coverage tool (`pytest-cov`) is configured for `backend/`; adding one in a future cycle would let subsequent `sdd-verify` passes report quantitative changed-file coverage instead of file-pairing inspection (same suggestion carried over from the prior `uml-command-bus` cycle, still unaddressed).

## Specs Synced to Main (openspec/specs/)

### New Capability Spec Created

1. **uml-document-persistence** — `openspec/specs/uml-document-persistence/spec.md` (new; no prior main spec existed for this domain, so the delta spec was copied mechanically in full, verified byte-identical via `diff -r`)
   - Document Creation (2 scenarios)
   - Document Read (2 scenarios)
   - Command Submission (3 scenarios)
   - Codec Round-Trip Correctness (1 scenario)
   - Tenant Scoping on Every Access (1 scenario)
   - uml_documents Import Boundary (1 scenario)
   - 6 requirements, 10 scenarios, all covered by passing tests

### Modified Main Specs

None. This cycle introduces one brand-new capability domain and touches no existing main spec. `apps/uml_modeling/` and `apps/uml_commands/` (and their corresponding main specs) are confirmed untouched — zero diff, re-verified independently at verify time.

## Archive Contents Verified

- [x] proposal.md — 2 open product questions recorded with stated working assumptions (permission role for command submission; document-creation input shape), both confirmed correct by the shipped implementation
- [x] exploration.md — present (optional artifact from sdd-explore)
- [x] specs/ — 1 new domain spec, fully copied (no delta merge needed, no pre-existing main spec)
- [x] design.md — 9 ADRs (DD1-DD9) documented and verified, all followed in code
- [x] tasks.md — 30/30 tasks complete and checked `[x]` across Phases 1-8
- [x] verify-report.md — Final Verdict PASS recorded (amended post-warning fix, final state 0 CRITICAL / 0 WARNING / 3 SUGGESTION)

## Native Review Receipt Gate

No `reviewGate` was present in structured status for this candidate — receipt-driven development was not engaged for this change (kill switch off / no review started). Archive proceeds under ordinary repository policy, consistent with the RDD contract's opt-in default.

## Task Completion Gate

All 30 implementation tasks across Phases 1-8 in the persisted `tasks.md` are checked `[x]`. No stale unchecked checkboxes were found; no reconciliation was required.

## Mechanical Copy Evidence

**NEW Domain Spec Copied** (shell `cp` + `mktemp` + `mv`, verified with `diff -r`):
```
uml-document-persistence: PASS (empty diff)
  source: openspec/changes/uml-document-persistence/specs/uml-document-persistence/spec.md
  dest:   openspec/specs/uml-document-persistence/spec.md
```

**Change Folder Moved to Archive** (shell `mv` — `git mv` reported "source directory is empty" because the change folder was untracked in git; fell back to plain `mv` per the skill's mechanical-move contract — verified with `diff -r` against a pre-move recursive snapshot):
```
Source snapshot → openspec/changes/archive/2026-09-12-uml-document-persistence
Verification: PASS (empty diff, no bytes altered or truncated)
```

## SDD Cycle Complete

This change has been fully planned (proposal), specified (1 new domain spec, 10 scenarios), designed (9 ADRs), implemented (30 tasks), verified (PASS with 0 CRITICAL, 0 WARNING after post-verify amendment), and archived.

**Ready for next SDD cycle.**

---

**Archive Report Created**: 2026-09-12
**Orchestrator**: sdd-archive
**Artifact Store Mode**: hybrid (Engram + openspec)
**Observation IDs**: #520 (spec) — no Engram observations found for proposal, design, tasks, or verify-report at archive time; all four were read directly from `openspec/changes/uml-document-persistence/` (filesystem, hybrid mode authoritative fallback). Apply-progress referenced by verify-report as Engram obs #523 (not independently re-read for this archive).
