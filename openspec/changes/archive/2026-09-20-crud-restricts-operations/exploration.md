# Exploration: crud-restricts-operations (DD147 tech debt)

Read-only exploration. Goal: make the declared `Table.profile.crud` (and `read_only`) restrict the endpoints the Spring generator emits and the `operations[]` the Domain Manifest lists.

## 1. Current state

- The controller template hardcodes six methods (`emit/templates/Controller.java.j2:15-45`: create, findById, update, delete, list, count) and the service template the same (`Service.java.j2:17-56`). Only `list` varies with the profile (`build_service_context`, `emit/context.py:731-845`, and `build_controller_context`, `:874-919`, via `_search_filters`, `_sortable_fields`, `_resolve_default_sort`). Imports are hardcoded sets (`context.py:883-901`, `:804-815`). File emission is unconditional (`renderer.py:193-199`); inheritance tables short-circuit and get no controller/service (`renderer.py:109`).
- `crud` and `read_only` are not read anywhere in the generator. There is one shared `RequestDto` and one `ResponseDto` (no per-operation DTOs).
- Parser: `_crud` (`profile_parser.py:61-79`) canonicalizes to the `create, read, update, delete` tuple; `[]` is accepted and yields `()` (declared empty, distinct from `None`). No cross-key check between `readOnly` and `crud`. The frontend panel maps tri-state "false" to `crud: []` (`GenerationProfilePanel.tsx:56-60`), so `[]` is a real user path.
- Precedent: the filtering/search change consumed the profile while keeping the 41-file oracle byte-identical when nothing is declared (`test_filtering_backward_compatibility.py`).

## 2. Manifest

`domain_manifest/builder/entities.py:10-35` holds the fixed `_OPERATIONS` tuple (six rows) and `_operations(resource_path)`, which returns `[]` only when there is no resource path. Pinned by `test_manifest.py` (`OPERATIONS` :21-28, `test_operations_exist_exactly_when_the_entity_has_a_controller` :53-59, the drift guard vs `api-docs.json` :153-161, and `test_declaring_crud_does_not_filter_the_operations` :282-290 which must be inverted) and by the spec requirements "CRUD Operations" and "CRUD Declaration Does Not Filter Operations" (both need a MODIFIED delta). The sample model declares no profile, so the drift guard, the Postman fixture and the boot-smoke gate (Customer) stay valid. Postman derives from the springdoc document, so it follows the controller with no code change.

## 3. Semantics proposal

- Mapping: create -> create; read -> findById, list, count; update -> update; delete -> delete. One pure `effective_operations(profile)` in `relational_mapping/domain/profile.py`, consumed by both the manifest and the Spring context builders so they cannot drift; canonical order = the controller's declaration order.
- Undeclared (`crud is None`, `read_only` in (None, False)): all six, byte-identical output. `Table.profile is None` and `TableProfile()` behave the same.
- `read_only=True` removes create, update and delete (fail-closed, deterministic intersection); `readOnly=False/None` leaves `crud` in charge.
- Service mirrors the controller (methods gated by flags, conditional imports); RequestDto, ResponseDto, Specifications and Repository stay always emitted.
- No parser rejection of `readOnly` + write `crud` (would break panel-authored models; DD133 "never invent").

## 4. Slicing and risks

Slice 1 (~200-300 lines): `effective_operations` + manifest filtering + spec deltas + DECISIONS_LOG. Slice 2 (~300-500 lines): generator flags, template gating, conditional imports, tests. Land back to back to avoid a transient manifest/generator divergence. Risks: models that already declared `crud`/`readOnly` (previously ignored) will get smaller APIs; unused Java imports; exact-list requirements ("six operations") need a review pass.

## 5. Functional decisions (for the user)

- D1: does `readOnly=true` restrict operations (recommended: yes, intersect)?
- D2: what does an effectively empty operation set (`crud: []`, or `readOnly=true` with `crud=[create]`) produce? (a) no controller/service, manifest `resourcePath: null` and `operations: []` (recommended); (b) an empty controller class.
- D3: `readOnly=true` with a write `crud`: silent intersection (recommended) vs parse-time rejection.
