# Exploration: UmlCommand + Command Bus (mutation/undo-redo layer on top of uml_modeling)

## Current State

`backend/apps/uml_modeling/` (built in the prior SDD cycle `canonical-uml-model`, verified 17/17 requirements, 33/33 scenarios, all passing) is a pure, framework-agnostic domain layer:

- **Layout** (one-directional, acyclic): `documents.py` → `domain/{ids,types,elements,model}.py` ← `validation/` (engine + `rules/*`). `domain/` is the leaf, imports nothing local.
- **Entities/value objects** (all `@dataclass(frozen=True)`, i.e. immutable):
  - `domain/elements.py`: `UmlAttribute`, `UmlParameter`, `UmlOperation`, `UmlClass`, `EnumerationLiteral`, `Enumeration`, `RelationshipEnd`, `Relationship` (kind: ASSOCIATION/AGGREGATION/COMPOSITION/GENERALIZATION), `Visibility`, `RelationshipKind`.
  - `domain/model.py`: `CanonicalUmlModel` (the aggregate) — `classes`, `enumerations`, `relationships` as tuples, plus opaque `generation_metadata: Mapping[ElementId, Mapping[str, object]]`. Read-only methods only: `class_by_id`, `enumeration_by_id`, `iter_named_elements`. `UmlModel = CanonicalUmlModel` (alias, same object — documented "D0" decision).
  - `documents.py`: `ProjectDocument` (the persistence envelope: `id: UUID`, `metadata`, `owner_id: str` — deliberately opaque, never imports `django.contrib.auth`, `model: CanonicalUmlModel`, `layout: DiagramLayout`, `revision: int`, timestamps). Also `ProjectMetadata`, `Position`, `DiagramLayout`.
- **Mutation methods that already exist**: only two, both on `ProjectDocument`, both whole-object replacements via `dataclasses.replace`, both bump `revision` and require an explicit `now: datetime` (domain stays clock-free, no `datetime.now()` calls — DD8):
  - `with_model(model, *, now) -> ProjectDocument`
  - `with_layout(layout, *, now) -> ProjectDocument`
  - **No mutation methods exist on `CanonicalUmlModel`, `UmlClass`, or any element** — there is currently no `add_class`, `rename_class`, `add_attribute`, etc. Any such mutation today would have to be done by hand-building a whole new `CanonicalUmlModel` (new tuples) and calling `document.with_model(new_model, now=...)`.
- **Immutability**: fully immutable by design (DD3: "frozen dataclasses + tuple ordered collections... `frozen` + `list` is only shallow immutability; command bus / undo-redo / optimistic revision need real snapshots" — this was an explicit forward-looking decision in the prior cycle anticipating this exact cycle).
- Validation (`validate(model, rules=RULES)`) is a pure function producing `ValidationResult`/`Diagnostic`s; separate concern from mutation, unaffected by this cycle's needs except that commands will likely want to re-validate after each mutation.
- Test suite: one test module per unit under `backend/apps/uml_modeling/tests/` (`test_elements.py`, `test_model.py`, `test_documents.py`, `test_ids.py`, `test_types.py`, `test_engine.py`, `test_diagnostics.py`, `test_apps.py`, `test_rules_*.py`, `test_validation_integration.py`, `factories.py`), matching the "~80 unit tests" description.

## Existing Patterns (or lack thereof)

Searched broadly across `backend/` and `frontend/src/**/*.{ts,tsx}` for `Command`, `dispatch`, `EventBus`, `undo`, `redo`, `history`, `Dispatcher`:

- **No Command object, dispatcher, event bus, event log, or undo/redo mechanism exists anywhere in the codebase**, backend or frontend. The only backend hit for "Command" is `apps/organizations/management/commands/seed_demo.py`, an unrelated Django management command (CLI seeding script), not a domain Command pattern.
- This confirms the cycle is greenfield for this abstraction — nothing to reconcile or migrate, no conflicting pattern to avoid.

## How the domain layer is invoked today

- `uml_modeling` is **fully unwired/orphaned**, exactly as designed for its own cycle. References to `uml_modeling` across `backend/` exist only in: `config/settings.py` (the `INSTALLED_APPS` line), the app's own files, and its own tests.
- **No API views, serializers, routers, or urlconf reference it.** There is no `api.py`/`schemas.py`/`views.py` in `uml_modeling` at all (confirmed via the prior design doc's file-changes table: "No models.py, no migrations, no urlconf, no schemas.py"). Compare to `apps/organizations` and `apps/users`, which do have `api.py`, `services.py`, `models.py`.
- There is currently **no application/service layer above `uml_modeling`** anywhere in the repo. This cycle would be the first to introduce one (the Command Bus itself would likely be that layer, or sit just below an eventual API layer).

## Persistence Story

- **No UML-diagram persistence model exists yet.** Django `models.Model` subclasses across `backend/` are limited to: `apps/users/models.py::EmailToken`, `apps/organizations/models.py::Organization` and `TenantScopedModel`. Nothing for `ProjectDocument`, diagrams, or commands.
- `uml_modeling` is **entirely in-memory/pure** today — `ProjectDocument` is a plain frozen dataclass, not a Django model; there are no migrations for this app (migrations exist only for `users` and `organizations`).
- Infra a future persistence layer could reuse: `docker-compose.yml` already runs `postgres:16-alpine` (service `db`), and the existing apps (`users`, `organizations`) establish the migration convention (`0001_initial.py`, incremental numbered migrations, `TenantScopedModel` base class for tenant-scoped models in `organizations/models.py`). Any future `ProjectDocument`/diagram persistence model would naturally extend `TenantScopedModel` to stay tenant-isolated, consistent with the existing multi-tenant convention.
- **No command-history or event-sourcing table exists** — if undo/redo needs persisted history, that storage is 100% new for this cycle (or deferred).

## Frontend State

- Frontend is still **limited to auth/org/member-management/dashboard screens**: `frontend/src/app/` contains only `(auth)/{login,register,verify-email,forgot-password,reset-password}`, `(gate)/select-organization`, `(app)/{dashboard,settings/members}`, plus the root landing page. No canvas, editor, or diagram-related route exists.
- No UML canvas/editor component exists anywhere in `frontend/src` (a few unrelated grep hits for "canvas/diagram/editor" were false positives — landing-page copy, role labels).
- **Confirmed: this is purely a backend-domain cycle for now.** No frontend UI work is implied or needed by introducing `UmlCommand` + Command Bus at the domain layer.

## Prior-Cycle Decisions Relevant Here (Engram `sdd/canonical-uml-model/design`, obs #384)

- **DD3** explicitly named this cycle's need as the reason for frozen+tuple immutability: real snapshots are required for "command bus / undo-redo / optimistic revision," ruling out in-place mutation on existing dataclasses as the mutation strategy — commands should produce new immutable value objects, not mutate fields.
- **DD8**: mutation helpers (`with_model`, `with_layout`) take an explicit `now: datetime` — any new command-level mutation helpers should follow the same clock-injection convention to keep the domain deterministic/testable (no `datetime.now()` inside domain code).
- **Open question D7** (still unresolved): "intra-backend imports permitted" between apps — deferred because the prior cycle shipped only one app. This cycle is the second backend app-relevant decision point: if the Command Bus becomes a second Django app, D7 needs to be settled — can it import from `apps.uml_modeling`, and can it stay import-clean itself?
- The user has a standing preference for **one Django app per domain**, never mixing domains in one app (per project memory `django-app-per-domain-preference`). This is directly relevant: should the Command Bus live inside `apps/uml_modeling/` (as a new `commands/` subpackage) or as its own new app? Domain-purity argues for keeping `uml_modeling` a pure model+validation library and putting the Command Bus in a distinct app/module that depends on it (matches D7's "acyclic, domain as leaf" spirit and the one-app-per-domain convention) — but this is a genuine option to weigh, not a foregone conclusion.

## Architecture Options & Tradeoffs

### A. Command Bus placement
1. **New subpackage inside `apps/uml_modeling/`** (e.g. `apps/uml_modeling/commands/`) — Pros: no new app registration, trivially reuses domain types without any cross-app import question, fastest to ship. Cons: blurs the "pure model + validation" boundary the prior cycle established; risks becoming a dumping ground if later cycles (persistence, realtime) also want to live "close to the domain."
2. **New sibling app** (e.g. `apps/uml_commands/` or `apps/command_bus/`) depending on `apps/uml_modeling` — Pros: matches the project's one-app-per-domain convention, keeps `uml_modeling` frozen as pure domain+validation (its own tests/scope stay exactly as verified), forces D7 (intra-backend imports) to finally be settled explicitly. Cons: one more app to wire into `INSTALLED_APPS`/settings; slightly more ceremony for what is currently a small abstraction (command dataclasses + a dispatch function).

### B. Command Bus mechanism
1. **Thin in-process dispatcher** (a registry mapping a `Command` type/tag to a handler function, similar in spirit to the existing `validate(model, rules=RULES)` registry pattern already established in `validation/engine.py`) — Pros: consistent with the codebase's existing explicit-registry style, no new dependency, trivially testable with fake handlers, zero framework coupling. Cons: none significant for current scope; needs a decision on whether handlers return a new `CanonicalUmlModel`/`ProjectDocument` or a diff/patch.
2. **Heavier framework** (generic CQRS/event-sourcing library, in-process pub/sub with subscribers, async task queue integration) — Pros: more future-proof if collaborative real-time editing (an eventual, unconfirmed goal) needs broadcast semantics. Cons: premature — no persistence, no realtime transport, no multi-user concurrency exists yet; disproportionate complexity; risks violating "pure domain, framework-agnostic" if the library pulls in async/Django/Channels concerns at this layer.

### C. Undo/redo state location
1. **Deferred entirely (out of scope this cycle)** — commands mutate the in-memory model and produce a new `ProjectDocument` revision; no undo/redo yet, just the Command abstraction + dispatcher + apply semantics. Pros: matches "no persistence layer exists yet" reality; keeps this cycle scoped and shippable, consistent with how `canonical-uml-model` itself was scoped tightly. Cons: "Command Bus" without undo/redo may undersell the point of introducing commands (though commands are also justified purely by giving mutation a structured, auditable API even without undo).
2. **In-memory per-session command stack** (a stack of applied commands + inverses, held wherever `ProjectDocument` currently lives) — Pros: enables undo/redo without any DB work this cycle; low complexity. Cons: lost on process restart; still needs *some* holder/session concept that does not exist yet — implicitly requires deciding where that holder lives.
3. **Persisted command log** (event-sourced: store every applied `UmlCommand` in the DB, replay to reconstruct state) — Pros: durable undo/redo across sessions, natural fit for eventual collaborative editing. Cons: requires introducing DB persistence for the first time — a materially bigger, separately-reviewable piece of work; conflates two concerns (introducing commands vs. introducing persistence) if not split explicitly.

### D. Should this cycle also introduce diagram persistence?
Given zero persistence exists today and the prior cycle was deliberately scoped narrow (validation only, explicitly rejecting models/migrations/API in its own design doc), the pattern established favors **keeping this cycle pure-domain too**: introduce `UmlCommand` + Command Bus operating on in-memory `CanonicalUmlModel`/`ProjectDocument` objects only, with persistence explicitly deferred to a later cycle. Committing to full event-sourced persistence in the same cycle would roughly double the scope (new Django app or models, migrations, a store/service layer, likely first API endpoints too) — a legitimate option, but a materially different-sized cycle that should be an explicit choice, not a silent default.

### E. Coupling risk — must not break "pure domain, framework-agnostic"
Any option that makes the Command Bus reach into Django (models, ORM sessions, request/response objects) at the same layer as domain mutation risks violating the established purity. The safest path (regardless of A/B/C choice): Command objects and the dispatcher stay plain Python (dataclasses + functions, no Django imports), exactly like `uml_modeling`'s existing `validate()`/`Rule` pattern — any Django/DB/API concern belongs in a layer *above* the bus. Placement option A.1 (subpackage inside `uml_modeling`) has a slightly higher risk of "just importing Django since it's already an app" by accident; option A.2 (separate app) makes the dependency direction and purity boundary more visible and enforceable, at the cost of one more app.

## Open Questions for the User

1. **Scope**: stay pure-domain (Command Bus operating on in-memory objects only, undo/redo deferred or in-memory-stack-only), or also introduce the first persistence model for `ProjectDocument`/diagrams? Changes cycle size substantially.
2. **App placement**: subpackage inside `apps/uml_modeling/`, or a new sibling app? Resolves the prior cycle's open D7 question and interacts with the one-app-per-domain convention.
3. **Undo/redo ambition this cycle**: full undo/redo (needs a stack or log + a holder for it), or structured mutation via commands only, with undo/redo explicitly deferred to a follow-up cycle?
4. Should command handlers auto-invoke `validate()` after applying a command, or stay decoupled as today (validation is a separate, caller-invoked step)?
