# session-log (issue #17)
Objective: a per-diagram log of who did what (people and the AI), grouped into sessions, filterable and exportable.
Branch: feature/session-log. Delivery: work-unit commits, one PR with `Closes #17`. Runner: backend `docker compose run --rm backend pytest`, frontend `npm test -- --run`.

## Specs
- S1: "Cada cambio y cada decisión sobre una propuesta de la IA queda registrado con autor y hora." Every change applied to the diagram and every proposal decision is recorded with its author and time.
- S2: "Se puede filtrar por sesión y por usuario." The log can be filtered by session and by user (the AI counts as a user).
- S3: "Los registros no se pueden editar." Entries are append-only: no endpoint writes or edits them, and the model, queryset and manager refuse update/delete.
- S4: "Solo los miembros de la organización la ven." Any member reads and exports; another organization gets 404.
- S5 (decision, user: "Apliquemos lo recomendado"): a session is a period of activity in the diagram. A new session starts after 30 minutes without any log entry in that diagram; sessions are numbered per diagram.
- S6 (from the issue scope): the log holds "cambios de personas y de la IA, propuestas aprobadas o rechazadas y mensajes del chat. Se puede consultar y exportar." Export is a CSV file that respects the filters.
- S7 (assumption): logged kinds are `change` (a command batch applied by a person or by approving a proposal), `version.restored`, `diagram.replaced` (XMI import into the diagram), `proposal.created` (author: the AI), `proposal.approved`, `proposal.rejected`, `chat.message` (a person or the AI). Not logged: diagram creation, saving a version, a proposal turning stale, drags.
- S8 (assumption): VIEWERs read and export too (the issue says only members see it); the CSV neutralizes spreadsheet formulas because chat text is user-controlled.
- Out of scope (from the issue): the version history, which already exists.

## Tasks
- T1 — S2,S3,S4,S5,S6,S8 — inline — complete — New app `apps.session_log`: append-only `LogEntry` (migration 0001), `record`, session assignment, listing with filters, sessions summary, CSV export, endpoints `GET .../log`, `.../log/sessions`, `.../log/export`; Risk: item 1 (additive new table, no existing data touched); evidence: RED (import error) then GREEN, 38 tests incl. immutability, sessions, filters, tenant isolation, CSV formula neutralization; commit bc00c39.
- T2 — S1,S7 — inline — complete — Hooks: `actor` on `submit_command(s)`/`restore_version`/`replace_document_content` and the API callers, voice/image confirm, proposals (created/approved/rejected), chat messages; the uml_documents and ai_assistant import-boundary tests allow `apps.session_log` (the new app has its own boundary test); Risk: item 3 (the optional `actor` keyword was added to shared service functions; existing callers and tests are unchanged and the default still logs, as the system); evidence: RED (TypeError on `actor`) then GREEN, backend suites of session_log, ai_assistant, uml_documents, organizations and xmi_interop 513 passed, then the full backend suite; commit c20570c.
- T3 — S2,S6 — inline — complete — Frontend: `lib/session_log.ts`, `state/session_log.ts`, `ActivityLogDialog` (session and user filters, CSV export), opened from a "Bitácora" button in the diagram header; Risk: none; evidence: RED then GREEN, frontend 78 files / 543 tests, `tsc` and ESLint clean; real browser with editor and viewer and the real OpenAI provider: a direct change, chat, the AI's proposal and its approval were logged, the viewer filtered by AI and exported a CSV; commit: see git log.

## Log
- L1 (2026-11-07, user): issue #17 — "bitácora de sesiones del diagrama"; chose "Apliquemos lo recomendado" for what a session is (a period of activity that ends after 30 minutes of inactivity).
