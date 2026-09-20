# Session 2026-09-20 - relational-generation-metadata (apply, verify, archive)

- Phase: `sdd-apply`, Strict TDD, Docker-only tests. 34/34 tasks. Final status: verified (PASS WITH WARNINGS, 0 critical) and archived, uncommitted, at `openspec/changes/archive/2026-09-20-relational-generation-metadata/`; delta specs `generation-profile` (new) and `relational-mapping` (modified) merged into main specs.
- Delivered: profile value objects, strict pure parser (12 rules), `InvalidGenerationProfileError`,
  `Column.profile` / `Table.profile`, mapper wiring (`_collect_profiles`, STI root rule, synthetic
  columns without profile). Decisions DD132-DD141 in `DECISIONS_LOG.md`.
- Tests (final, at archive): backend suite 987 -> 1070 passed; `apps/relational_mapping` 138 passed; `apps/domain_manifest` 88 passed. Mutation checks
  1-7 each produced red tests and were reverted (tree green again).
- Findings: `Table` is unhashable (pre-existing), so hash checks target `Table.profile` / `Column`;
  a guard forbids other apps importing `apps.domain_manifest`, so the manifest neutrality test lives
  in `domain_manifest/tests/`; authored size (~960 lines, mostly triangulated tests) exceeds the 800-line budget and was accepted as `size:exception`.
- Accepted warnings: `Table`/`RelationalModel` already unhashable (spec amended); manifest half of the neutrality test lives in `apps/domain_manifest/tests`; `InvalidGenerationProfileError` not imported in `mapper.py` (design wiring table lists it, not needed); three tests pass by construction (protected by mutation checks).
- Next: commit (never `.pi/`), then candidates: manifest emission of the profile, Spring filtering/search, an authoring path, §37 item 12 remainder, Flutter frontend.
- Gate results: 41-file Spring oracle, inheritance sha256 goldens and manifest tests green, no
  expectation edited; `domain_manifest` / `spring_generator` sources untouched.
