# Second partial traceability matrix

This is the working baseline for the authorized second-partial scope. Statuses
describe repository evidence, not promised completion.

| Scope | Baseline status | Reused foundation | Planned task | Acceptance evidence |
| --- | --- | --- | --- | --- |
| S1 — Version control | Implemented (`ea1c9ff`) | Tenant-scoped `UmlDocument`, canonical codec, row-locked command submission | T2 | Backend 149 tests, frontend 67 files / 432 tests, TypeScript check and independent verification passed. |
| S2 — Generated backend in cloud VM | Partial | Spring ZIP generator, runner, deployment model/UI and production Compose | T6 | An authorized remote target records source revision, URL, health and sanitized events; stop/redeploy requires confirmation. |
| S3 — Diagram templates | Missing | Canonical model codec, document creation and organization membership | T3 | A template creates an independent document with remapped IDs; inaccessible across organizations. |
| S4 — Database preview | Partial | Authoritative `map_to_relational` pipeline and join-table hints | T4 | Preview and DDL derive from the same `RelationalModel`; no database mutation occurs. |
| S5 — Architecture audit | Missing | Canonical UML validation and optional on-device local-assistant baseline | T5 | A deterministic cycle fixture produces a revision-bound finding offline; audit never changes UML. |

# AI participation traceability (GitHub #15-#19)

Source request: "la IA sera un desarrollador mas todas las ideas que la IA tenga se mostrara en la pizarra mientras un desarrollador lo permita". Feature document: `odd/tasks/ai-board-proposals.md`.

| Issue | Status | Evidence |
| --- | --- | --- |
| #15 AI proposes changes on the board | Implemented on `feature/ai-board-proposals` (trigger A: a developer asks) | `apps/ai_assistant/proposals.py`, `models.AiProposal`, `POST/GET /ai-proposals`, `.../approve\|reject`, `proposal.update` socket event, `AiProposalsPanel`, dashed drafts in `DiagramCanvas`. Complete suggestions (classes with attributes, operations and relationships) and per-change selective approval added after trying it with the real AI. Backend ai_assistant + uml_documents + organizations 365 passed; frontend 476 passed; verified in a real browser with the real provider (viewer read-only, editor approves a selection, live update). |
| #15 follow-up: trigger B (AI proposes on its own) | Planned | Agreed order: A first, then B as another trigger over the same proposal pipeline. |
| #16 Group chat, one model, shared context | Implemented on `feature/ai-group-chat` (the AI answers only when mentioned with `@IA`) | `apps/ai_assistant/chat.py`, `models.ChatMessage` (migration 0003), `GET/POST /chat`, `chat.message` socket event, `ChatPanel`, `lib/ai_chat.ts`. Feature document `odd/tasks/ai-group-chat.md`. Backend ai_assistant + uml_documents + organizations 397 passed (includes a threaded simultaneous-writers test); frontend 504 passed; verified in a real browser with three users and the real provider (live delivery, same order for all, AI answered with the shared context, viewer read-only). |
| #17 Session log | Implemented on `feature/session-log` (a session = a period of activity; a new one starts after 30 minutes without any entry in the diagram) | `apps/session_log` (`LogEntry`, migration 0001, `services.record/record_change/list_entries/list_sessions/export_csv`, `GET .../log`, `.../log/sessions`, `.../log/export`), hooks in `uml_documents.services` (`actor` on `submit_command(s)`, `restore_version`, `replace_document_content`), `ai_assistant.proposals` and `chat`, `ActivityLogDialog` + `lib/session_log.ts` + `state/session_log.ts`. Feature document `odd/tasks/session-log.md`. Entries are append-only (model, queryset and managers refuse update/delete; no write endpoint); members only (VIEWER included), other organizations get 404. Verified in a real browser with the real provider: changes, chat, the AI's proposal and its approval were logged; filters by user and session; CSV export. |
| #18 Optional local AI | Planned | Independent of #15. |
| #19 Mobile collaboration and push notifications | Planned | Needs a push-service decision (e.g. FCM) and its credentials outside the repo. |

## Evidence conventions

- Record the exact commit, command, environment and observed result when each
  task is completed.
- Mark a remote-VM claim as verified only after an explicitly authorized run
  against that destination.
- Treat AI explanations as optional assistance. Deterministic rules remain the
  authoritative audit output.
