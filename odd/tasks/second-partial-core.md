# Second partial core capabilities

Objective: implement the authorized second-partial capabilities incrementally on `feature/voice-command-preview`; delivery: ask-on-risk; runners: Docker Compose pytest, frontend Vitest, Flutter tests where applicable.

## Specs

S1. "implementar un control de versiones, para tener un mejor control de los diagramas."

S2. "Como segundo punto se tiene la idea, que genere el backend y lo despliegue, en una maquina virtual en la nube, por medio de contenedores, no solo que cree el backend por medio de codigo."

S3. "Como tercer punto plantillas para los diagramas del proyecto lo cual facilite a la hora de usar la aplicacion o sistema."

S4. "Como cuarto punto una vista previa a la base de datos antes de generarla."

S5. "Como quinto punto auditor inteligente ademas de validar UML, podria analizar la calidad arquitectonica."

## Tasks

- T1 — S1-S5 — inline — complete — Established baseline and traceability; route: inline because no writer trigger applies; evidence: repository audit plus `docs/ai/TRACEABILITY_MATRIX.md`; commit: pending.
- T2 — S1 — inline — complete — Added immutable UML snapshots, history, structural comparison, explicit-confirmation restoration and UI; Risk: item 1 (restoration changes persisted UML content); evidence: backend 149 tests, frontend 67 files / 432 tests, TypeScript check and independent verifier passed; commit: `948eb99`.
- T3 — S3 — inline — pending — Add tenant-scoped template catalogue, publication and independent document instantiation; Risk: item 1 (persisted template and document data); commit: pending.
- T4 — S4 — inline — pending — Expose a full read-only relational preview and deterministic SQL export from the authoritative mapper; Risk: none; commit: pending.
- T5 — S5 — inline — pending — Add deterministic architectural audit findings, optional local-AI explanation boundary and report export; Risk: item 3 (new consumed audit contract); commit: pending.
- T6 — S2 — inline — pending — Add remote deployment governance, source-revision/event evidence and confirmed lifecycle actions; Risk: item 2 and 5 (remote authorization, infrastructure and credentials); commit: pending.
- T7 — S1-S5 — inline — pending — Complete integrated verification, academic traceability and user evidence; Risk: none; commit: pending.

## Log

L1 — User authorization (verbatim): "ok, ahora tambien lo siguiente:
\"implementar un control de versiones, para tener un mejor control de los diagramas.
Como segundo punto se tiene la idea, que genere el backend y lo despliegue, en una maquina virtual en la nube, por medio de contenedores, no solo que cree el backend por medio de codigo.
Como tercer punto plantillas para los diagramas del proyecto lo cual facilite a la hora de usar la aplicacion o sistema.
Como cuarto punto una vista previa a la base de datos antes de generarla.
Como quinto punto auditor inteligente ademas de validar UML, podria analizar la calidad arquitectonica. \"

L2 — Repository audit: revision locking, the canonical UML model, relational mapper, Spring archive generation, runner, tenant boundaries and deployment UI are reusable. Immutable version history, templates, full relational preview/DDL, architecture audit and remote-target governance remain absent or partial.

L3 — Remote operations are not authorized by local implementation authorization. T6 may prepare local code and tests, but contacting or changing a VM requires explicit destination, operation and credential/session authorization.

L4 — T1 complete: recorded current reusable foundations, missing capability boundaries and acceptance evidence in `docs/ai/TRACEABILITY_MATRIX.md`. Next implementation task is T2, immutable UML version history.

L5 — T2 complete: `UmlVersion` stores tenant-bound JSON snapshots with sequential version numbers, source revision, author and optional description. History/compare read snapshots only; restore requires an explicit UI confirmation and expected-revision validation under the document row lock, then writes a new revision and broadcasts it. Independent high-risk verification found no blockers.

L6 — T2 delivery: committed as `948eb99 feat(uml): add diagram version history`. Native assessment is high risk (item 1); receipt-driven development is clone-locally disabled, so no native review lifecycle was started. Assessment explicitly excluded two user-owned untracked files.
