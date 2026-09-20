# Session 2026-09-20 - uml-generation-profile-authoring (apply)

- Phase: `sdd-apply`, Strict TDD, Docker-only tests, in two attempts (Phases 1-5 first, Phase 6 docs second). Status: applied, verify pending, uncommitted; 31/31 tasks. The last commit is `cdae44c feat(domain-manifest): emit declared generation profile`.
- Delivered (backend slice 1 of 2): `SetGenerationProfile` command (`commands.py`, `schemas.py`, `dispatcher.py`), handler `handlers/generation_profile.py` with the shared prune primitive used by `RemoveClass` / `RemoveAttribute`, and the `services.submit_command` gate (level inference, verbatim parser messages, `defaultSort` resolution). Decisions DD151-DD159 in `DECISIONS_LOG.md` (DD154 first named import-guard exception; DD158 corrects the same-class-only pruning rule).
- Tests: backend 1107 -> 1184 passed; `apps/uml_commands` 86, `apps/uml_documents` 134, `relational_mapping` + `domain_manifest` + `spring_generator` 588.
- Mutation checks M1-M10 and S1-S3 run and reverted, all killed. M8 "outside the lock" is an equivalent mutant single-threaded; tests 2.9, 3.1, 3.2 are characterization tests proven by mutation.
- Size: ~1208 authored lines (source ~221, tests ~987) plus docs; `size:exception` accepted (standing user choice, tests not trimmed).
- Untouched (git diff empty): `frontend/`, `apps/uml_modeling`, `apps/relational_mapping`, `apps/spring_generator`, `apps/domain_manifest`, `docker-compose.yml`, `scripts/`.
- Next: `sdd-verify`, archive (merge both MODIFIED requirements and the rescoped scenarios), commit (never `.pi/`); then frontend change `uml-generation-profile-panel`, then Spring filtering/search, then `crud` restricting `operations[]`.
