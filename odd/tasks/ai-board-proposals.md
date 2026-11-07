# AI board proposals (GitHub #15)

Objective: the AI acts as one more developer; its ideas appear on the board for everyone and are applied only when an OWNER/EDITOR approves. Branch `feature/ai-board-proposals`; delivery strategy ask-on-risk; runner: backend `docker compose run --rm backend pytest`, frontend `npm test -- --run`.

## Specs
- S1: "La IA propone cambios en la pizarra como un desarrollador más". An AI proposal is a draft that never modifies the document until approved.
- S2: "Una propuesta de la IA aparece en la pizarra sin modificar el documento." Every organization member sees pending proposals in real time (WebSocket).
- S3: "Un OWNER o EDITOR puede aprobarla o rechazarla." "Un VIEWER no puede aprobar ni rechazar."
- S4: "Una propuesta pierde vigencia si cambia la revisión del diagrama." A stale proposal cannot be approved.
- S5: "El cambio aprobado queda identificado con la IA como autora." Proposals record who requested and who decided.
- S6 (assumption): trigger A only (a developer asks the AI for an idea). Trigger B (the AI proposes on its own) is a documented follow-up.
- S7 (assumption): proposals are organization-scoped; another organization never sees or decides them.

## Tasks
- T1 — S1,S4,S5,S6,S7 — inline — complete — AiProposal model + migration `ai_assistant/0001`, `proposals.py` (create/list/get/approve/reject, lazy stale) reusing Translator and `submit_commands`; Risk: none (additive table, no existing behavior changed; `service.py` only gained two public aliases); evidence: RED ImportError then GREEN; commit: see git log.
- T2 — S2,S3 — inline — complete — `POST/GET /ai-proposals`, `POST .../approve|reject` (OWNER/EDITOR decide, any member lists), `proposal.update` event relayed by `DocumentConsumer.proposal_update` after re-authorizing membership; Risk: none; evidence: RED 10 failures then GREEN; backend ai_assistant + uml_documents + organizations 349 passed, no pending migrations; commit: see git log.
- T3 — S2,S3 — inline — pending — Frontend: client, live state, proposals panel with approve/reject, dashed draft classes on the canvas; commit: pending.
- T4 — all — inline — pending — Docs/traceability and manual browser verification; commit: pending.

## Log
- L1 (2026-11-07, user): "la IA sera un desarrollador mas todas las ideas que la IA tenga se mostrara en la pizarra mientras un desarrollador lo permita" and "Hasta el momento la participacion de la IA es baja, dar mas protagonismo a la IA".
- L2 (2026-11-07, user): chose trigger A first, "luego implementar la B".
