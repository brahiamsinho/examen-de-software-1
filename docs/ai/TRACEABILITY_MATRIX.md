# Second partial traceability matrix

This is the working baseline for the authorized second-partial scope. Statuses
describe repository evidence, not promised completion.

| Scope | Baseline status | Reused foundation | Planned task | Acceptance evidence |
| --- | --- | --- | --- | --- |
| S1 — Version control | Implemented (`948eb99`) | Tenant-scoped `UmlDocument`, canonical codec, row-locked command submission | T2 | Backend 149 tests, frontend 67 files / 432 tests, TypeScript check and independent verification passed. |
| S2 — Generated backend in cloud VM | Partial | Spring ZIP generator, runner, deployment model/UI and production Compose | T6 | An authorized remote target records source revision, URL, health and sanitized events; stop/redeploy requires confirmation. |
| S3 — Diagram templates | Missing | Canonical model codec, document creation and organization membership | T3 | A template creates an independent document with remapped IDs; inaccessible across organizations. |
| S4 — Database preview | Partial | Authoritative `map_to_relational` pipeline and join-table hints | T4 | Preview and DDL derive from the same `RelationalModel`; no database mutation occurs. |
| S5 — Architecture audit | Missing | Canonical UML validation and optional on-device local-assistant baseline | T5 | A deterministic cycle fixture produces a revision-bound finding offline; audit never changes UML. |

## Evidence conventions

- Record the exact commit, command, environment and observed result when each
  task is completed.
- Mark a remote-VM claim as verified only after an explicitly authorized run
  against that destination.
- Treat AI explanations as optional assistance. Deterministic rules remain the
  authoritative audit output.
