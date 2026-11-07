# ai-group-chat (issue #16)
Objective: one chat per diagram where several developers talk and one AI model answers with everyone's context.
Branch: feature/ai-group-chat. Delivery: single PR per work unit group, `Closes #16`. Runner: backend `docker compose run --rm backend pytest`, frontend `npm test -- --run`.

## Specs
- S1: "Todos los participantes ven los mensajes en tiempo real." Messages are broadcast on the existing document socket (`chat.message`), including to VIEWERs.
- S2: "El modelo recibe el contexto de todos, con el autor de cada mensaje." The transcript sent to the model lists every recent message as `Author: text`, plus the diagram context.
- S3: "Dos usuarios que escriben a la vez no se mezclan ni pierden mensajes." Every message is its own persisted row with a database-assigned order; nothing is kept in a shared in-memory cache.
- S4: "Una organización nunca ve el chat de otra." Every read and write goes through the org+document check; another organization gets 404.
- S5 (decision, user: "usemos lo recomendado"): the AI answers only when a message mentions `@IA`; other messages are just stored and shown. Never to every message.
- S6 (assumption): OWNER/EDITOR write; VIEWER only reads (same as AI proposals).
- S7 (risk from the issue, "Límite de tokens del contexto y costo por organización"): the model only receives the last 30 messages, and a message is at most 2000 characters.
- S8: "Creo que nos los esta implementando" (user, seeing the AI say "Voy a agregar las tablas 'Roles', 'Permisos' y 'Usuarios'" with nothing added). When the team asks the AI in the chat to add or change something, it leaves a pending draft on the board (never an applied change) and says so; it must never claim it already changed the diagram.
- Out of scope (from the issue): approving proposals and the session log.

## Tasks
- T1 — S1,S3,S4,S6 — inline — complete — `ChatMessage` model + migration `0003`, `chat.py` (post/list/serialize/broadcast), endpoints `GET/POST .../chat`, socket handler `chat_message`; Risk: item 1 (additive new table, no existing data touched); evidence: RED (import error) then GREEN, 32 backend tests incl. a threaded simultaneous-writers test; commit: see git log.
- T2 — S2,S5,S7 — inline — complete — `@IA` mention triggers one model reply through the `reply_in_chat` tool (no new client method); context with authors, capped at 30 messages; Risk: none (additive; voice/image/proposal paths untouched); evidence: tests for mention detection, authors in order, cap, model failure, empty reply; real OpenAI answered using the shared context; commit: see git log.
- T3 — S1,S6 — inline — complete — Frontend: `lib/ai_chat.ts`, `ChatPanel`, live messages via `onChat` in `openDocumentSocket`/`useDocument`, mounted in the diagram page; Risk: none; evidence: RED then GREEN, frontend 75 files / 504 tests, `tsc` and ESLint clean; real browser with editor, owner and viewer: live delivery, same order for all three, viewer read-only; commit: see git log.

- T4 — S8 — inline — complete — Chat suggestions become pending drafts (`proposals.propose_calls` shared with `create_proposal`; `suggest_uml_additions` offered next to `reply_in_chat`; `proposal` in the POST answer); Risk: none (additive; the panel's behavior is unchanged and the diagram still changes only on approval); evidence: RED (6 tests failed) then GREEN, backend 404 passed; real OpenAI left a draft, the diagram stayed at 6 classes until approval (then 7) and the viewer saw the draft without checkboxes; commit: see git log.

## Log
- L2 (2026-11-07, user, after trying the chat): "Creo que nos los esta implementando" (screenshot: the AI answered "Voy a agregar las tablas 'Roles', 'Permisos' y 'Usuarios'" but the diagram did not change). Cause: the chat model had only `reply_in_chat`, so it promised changes it had no way to make. Fix: S8.
- L1 (2026-11-07, user): issue #16 — "chat grupal con un único modelo de IA y contexto compartido"; chose "usemos lo recomendado" for when the AI answers (only when mentioned).
