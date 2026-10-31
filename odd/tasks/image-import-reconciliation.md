# Image import reconciliation

Objective: safely reconcile an existing UML diagram with a newer image by previewing proposed changes and requiring explicit confirmation before persistence.
Branch: `feature/image-import-reconciliation`; delivery: ask-on-risk; test runners: `docker compose exec -T backend pytest`, `npm test`.

## Specs

S1. "deberia de borrar esa clase lo mismo si agrego otro atributo o quito un atributo,etc."
S2. "muestre primero una vista previa de cambios —agregar, modificar y eliminar— y requiera tu confirmación antes de aplicar borrados"

## Tasks

- T1 — S1-S2 — inline — complete — Server-side preview plan and locked atomic confirmation; Risk: item 1 (persisted UML content may be removed); evidence: 237 backend tests passed.
- T2 — S1-S2 — inline — complete — Client preview dialog, cancel/apply flow, and UI tests; Risk: none; evidence: 430 frontend tests passed.
- T3 — S1-S2 — inline — complete — Verification and documentation; Risk: item 1 (T1); evidence: high-risk recheck resolved both blockers.

## Log

L1 — User request (verbatim): "perfecto, ahora quiero que se pueda editar con imagenes ejemplo si 
subo esto:

deberia de borrar esa clase lo mismo si agrego otro atributo o quito un atributo,etc."

L2 — User approved the safeguard (verbatim): "tienes mucha razon implementemoslo"

L3 — Decision: the backend will identify classes and members by exact visible names, making renames appear as an addition plus a removal in the preview. This avoids guessing destructive rename intent from an image.

L4 — Route: inline. The task is tracked because deleting persisted diagram content is high-risk. No writer trigger applies; an independent verifier will run after focused checks for the item-1 change.

L5 — Implemented a preview-only image endpoint and a confirmation endpoint. Preview plans bind organization, document and base revision, expire after 15 minutes, and confirmation checks the revision under the document row lock before applying the batch.

L6 — Verification: `docker compose exec -T backend pytest apps/ai_assistant apps/uml_documents` — 237 passed; `frontend/npm test` — 66 files / 430 tests passed. Independent verifier initially found a legacy direct-write route and a stale-plan race; both were corrected and rechecked as resolved.

L7 — User delivery decision (verbatim): "un solo commit es perfecto, aunque sea gigante"

L8 — Delivery: committed as `411d0ff feat(ai): preview image reconciliation changes`. Receipt-driven development is clone-locally disabled; native assessment classified the committed candidate as high risk due to persisted UML deletion, but no review lifecycle was started.
