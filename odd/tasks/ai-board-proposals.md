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

- S8: "faltan atributos" — a proposal includes each new class's attributes and operations and the relationships between classes, not only class names. Existing classes/attributes/relationships are never duplicated.
- S9: "deberia de poder seleccionar la clase o todas, no que todas o ninguna" — the approver selects which proposed changes to apply (one, some or all); a selection is valid only if every selected change keeps what it depends on (an attribute needs its class, a relationship needs both classes).

## Tasks
- T1 — S1,S4,S5,S6,S7 — inline — complete — AiProposal model + migration `ai_assistant/0001`, `proposals.py` (create/list/get/approve/reject, lazy stale) reusing Translator and `submit_commands`; Risk: none (additive table, no existing behavior changed; `service.py` only gained two public aliases); evidence: RED ImportError then GREEN; commit: see git log.
- T2 — S2,S3 — inline — complete — `POST/GET /ai-proposals`, `POST .../approve|reject` (OWNER/EDITOR decide, any member lists), `proposal.update` event relayed by `DocumentConsumer.proposal_update` after re-authorizing membership; Risk: none; evidence: RED 10 failures then GREEN; backend ai_assistant + uml_documents + organizations 349 passed, no pending migrations; commit: see git log.
- T3 — S2,S3 — inline — complete — Frontend: `lib/ai_proposals.ts` (client, `upsertProposal`, `buildAiDrafts`), `proposal.update` handler in `openDocumentSocket`, `proposals`/`applyProposal` in `useDocument`, `AiProposalsPanel` ("IA como compañera" card), dashed violet draft boxes/edges in `DiagramCanvas` with a one-time refit when the draft set changes; Risk: none (additive; `DiagramCanvas` synthetic-element path reused, existing lifecycle tests unchanged apart from two mock methods); evidence: RED for each unit, frontend 72 files / 463 tests, TypeScript clean, ESLint clean on changed files (one pre-existing warning and the pre-existing `set-state-in-effect` error in `documents/[docId]/page.tsx` remain); commit: see git log.
- T4 — all — inline — complete — Docs/traceability plus real-browser verification (Playwright, headless): a viewer saw the draft and had no Aprobar/Rechazar/Pedir ideas controls; an editor approved it, the class and relationship became real and the viewer's open page cleared the draft live over the WebSocket; reject left the diagram untouched. A defect found there (draft off-screen before approval) was fixed with a failing test first. LLM answers were simulated with a fake client, so the real provider call is not exercised; commit: see git log.

- T5 — S8 — inline — complete — Structured `suggest_uml_additions` tool for proposals (classes with attributes/operations + relationships), expanded with the existing `expand_extraction` and de-duplicated against the diagram (`_additions_only`); Risk: none (additive; the voice/image paths and their tools are untouched); evidence: RED (tests failed before the tool existed) then GREEN; the real OpenAI model, which previously answered only `add_class`, now returned 8 changes with 4 attributes and 2 relationships; commit: see git log.
- T6 — S9 — inline — complete — Partial approval: optional `{"selected": [...]}` body on approve (bodyless POST still approves everything), `InvalidSelectionError` for an empty/out-of-range/dependency-breaking selection, `applied_indices` stored (migration `ai_assistant/0002`, additive nullable column), dependency-aware checkboxes with Todos/Ninguno in the panel (`toggleChange`); Risk: item 1 (additive nullable column, no existing data touched); evidence: RED then GREEN; backend ai_assistant + uml_documents + organizations passed, frontend 72 files / 476 tests, `tsc` clean; in a real browser with the real AI unchecking a class unchecked its 2 attributes and its relationship (4 of 8 left) and approving grew the diagram from 5 to 6 classes; commit: see git log.

## Log
- L1 (2026-11-07, user): "la IA sera un desarrollador mas todas las ideas que la IA tenga se mostrara en la pizarra mientras un desarrollador lo permita" and "Hasta el momento la participacion de la IA es baja, dar mas protagonismo a la IA".
- L2 (2026-11-07, user): chose trigger A first, "luego implementar la B".
- L3 (2026-11-07, user, after trying it with the real AI): "Esta bien, pero faltan atributos, deberia de poder seleccionar la clase o todas no que todas o ninguna,etc."
- Evidence for L3: the real model answered five add_class calls and nothing else (the same failure the image import already hit); approving applied all five. Cause: the one-call-per-change tool schema. Fix reuses the structured extraction approach.
