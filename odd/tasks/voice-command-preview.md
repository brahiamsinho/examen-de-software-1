# Voice command preview

Objective: make spoken UML edits previewable and explicitly confirmable before any diagram mutation.
Branch: `feature/voice-command-preview`; delivery: ask-on-risk; test runners: `docker compose exec -T backend pytest`, `npm test`.

## Specs

S1. "ahora funciona lka opcion por voz? lo mismo de editar implementar,etc."
S2. "mira, no importa lo que quiero es que implementemos lo de voz que te pedi asi que empezemos"

## Tasks

- T1 — S1-S2 — inline — complete — Tenant/document/revision-bound voice preview and atomic confirmation; Risk: item 1 (confirmed voice plans may remove persisted UML content); evidence: 242 backend tests passed.
- T2 — S1-S2 — inline — complete — Voice preview/cancel/confirm UI and tests; Risk: none; evidence: 430 frontend tests passed.
- T3 — S1-S2 — inline — complete — High-risk verification and continuity records; Risk: item 1 (T1); evidence: independent verifier found no blockers.

## Log

L1 — User request (verbatim): "ahora funciona lka opcion por voz? lo mismo de editar implementar,etc."

L2 — Clarification from the prior conversation: voice currently applies supported commands immediately; the intended new flow is interpret → preview → explicit confirmation → apply.

L3 — User authorization (verbatim): "mira, no importa lo que quiero es que implementemos lo de voz que te pedi asi que empezemos"

L4 — Decision: reuse the established image-preview safeguards for voice plans: cache-backed, organization/document/revision-bound plans that expire after 15 minutes, and expected-revision validation under the document row lock.

L5 — Route: inline. This is tracked high-risk work because a confirmed spoken command may remove persisted UML content. No writer trigger applies; an independent verifier is required after functional checks.

L6 — Voice uses the same plan safeguards as image import: a 15-minute cache-backed plan bound to organization, document and revision; only confirmation persists an atomic batch after expected-revision validation under the document row lock.

L7 — `remove_class` is now an available voice tool because the preview explicitly exposes its destructive effect before the user confirms it.

L8 — Verification: `docker compose run --rm backend pytest apps/ai_assistant apps/uml_documents` — 242 passed; `frontend/npm test` — 66 files / 430 tests passed. Independent high-risk verification found no blockers and independently checked preview, expiry, foreign-tenant and revision-race rejection.

L9 — Delivery: committed as this feature work unit. Native assessment is high risk because confirmation can delete persisted UML elements; receipt-driven development is clone-locally disabled, so no native review lifecycle was started.
