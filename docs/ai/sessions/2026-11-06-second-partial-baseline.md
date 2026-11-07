# Second partial baseline — 2026-11-06

The authorized second-partial scope has been converted into a tracked feature
document with seven tasks. The first task establishes traceability only; it
does not claim any new runtime capability is complete.

T2 is committed as `ea1c9ff`: immutable UML history, structural comparison
and safe restore are available through the web API and editor UI. The next
increment is tenant-scoped templates. Remote VM operations require separate
explicit authorization and must not reuse ambient credentials or sessions.

## Issue tracking

The user requested and manually confirmed four feature issues: GitHub #8
(organization-scoped templates), #9 (relational preview and SQL export), #10
(deterministic architecture audit), and #11 (remote VM deployment governance).
The user requested only feature issues, so integrated verification evidence
remains tracked locally as T7 without a GitHub issue.

## T3 implementation checkpoint

The local uncommitted T3 implementation adds organization-private template
storage, tenant-scoped APIs, recursive ID remapping on instantiation, editor
publication and a dashboard catalogue. Backend UML-document tests passed 152;
targeted frontend tests, TypeScript and targeted ESLint passed. The complete
frontend suite passed afterwards (68 files / 434 tests).
