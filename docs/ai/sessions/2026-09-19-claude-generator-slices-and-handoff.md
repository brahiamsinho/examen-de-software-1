# Session — 2026-09-19 — Generator slices, two bug fixes, handoff refresh

Work done in this session, in order (all on `main`, all pushed):

- Finished `2026-09-15-uml-node-position-sync`, then fixed a lock that stayed
  held forever (`f605592`: client-side self-expiry, because Redis TTL expiry
  broadcasts nothing). Added operations/methods to UML classes
  (`2026-09-16-uml-class-operations`, `e51df2a`).
- Rewrote git history once (twice, the first pass missed a commit) to remove
  `Co-Authored-By`/`Claude-Session` trailers; the user does not want AI
  attribution on the repo.
- `2026-09-17-uml-relational-mapping` (`ccb662c`): pure
  `CanonicalUmlModel → RelationalModel` mapper with Single Table inheritance,
  UUID PKs, native PG ENUM, FK/join-table rules, plus the
  `MULTI_PARENT_GENERALIZATION` validation rule.
- Fixed a 500 on every command while a WebSocket client was connected
  (`b00141e`): `channel_layer.group_send` uses msgpack, which rejects
  `UUID`/`datetime`. The UI showed a red box reading "null" because the
  frontend's `ApiError` parser stringifies a missing `detail` as `"null"`.
- Three Spring Boot generator slices, each a full SDD cycle:
  `spring-boot-generator-core` (`8b84467`),
  `spring-boot-generator-relationships-enums` (`b42a190`),
  `spring-boot-generator-application-api-layer` (`0aa211a`). Backend went
  from 442 to 631 tests.
- Refreshed `HANDOFF_LATEST.md`, `NEXT_STEPS.md` and the false header of
  `CURRENT_STATE.md` (it still said "nothing from the UML domain exists").

Decisions taken with the user: generated backends must not hardcode
host/port/URL; frontend/mobile generation is deferred (Flutter is intended
instead of the spec's Next.js PWA + Capacitor); item 13 will use an ephemeral
JVM/Gradle container with its own PostgreSQL; oversized cycles ship as one PR
under `size:exception`.

Open at the end of the session: Single Table inheritance generation is
blocked (`Column` has no owning-UML-class attribution), and it needs a user
decision. Details and the full backlog are in `NEXT_STEPS.md`.

Process notes worth keeping: every sub-agent report was re-checked by
re-running pytest; a rate-limit cut `sdd-apply` mid-cycle once, and the
recovery was to read `tasks.md` and the real test state before relaunching.
