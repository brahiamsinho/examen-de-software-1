# Design: Cycle 1 — Canonical UML Model, Project Document, Validation Engine

## Technical Approach

One new Django app `backend/apps/uml_modeling/` acting purely as a registration shell
(`apps.py` only). Inside it, three layers with a strictly one-directional dependency
graph, none of which import Django, Ninja, or Pydantic:

```
  documents.py ──────┐
   (envelope)        │
                     ▼
              domain/  (ids, types, elements, model)   ← leaf, imports nothing local
                     ▲
  validation/ ───────┘
   (diagnostics, engine, rules/)
```

`validation` reads `domain` and never mutates it; `documents` composes `domain`;
nothing imports `validation`. This satisfies proposal D7's operative rule (acyclic,
one-directional, domain as leaf) and keeps `validate()` callable from every future
entry point (HTTP, Channels, XMI, assistant) as the `uml-validation` spec requires.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | Two enforcement layers: **construction invariants** raise `ValueError`/`TypeError` in `__post_init__`; **model-level semantics** become `Diagnostic`s | Single layer (everything a diagnostic; or everything an exception) | Spec demands both: "class-typed attribute rejected" and "empty owner rejected" are constructor rejections, while duplicate names and dangling refs must be navigable, fixable, non-fatal |
| DD2 | Boundary rule for DD1: construction rejects only what is **unrepresentable/mistyped**; it never rejects user-fixable content | Validate ranges in `__post_init__` | `Multiplicity(-1, None)` and `Multiplicity(2, 1)` MUST be constructible, otherwise `INVALID_MULTIPLICITY` can never be produced. `Multiplicity` is a deliberately unvalidated value object |
| DD3 | All dataclasses `frozen=True`; ordered collections typed `tuple[...]`, maps as read-only `Mapping` | Mutable dataclasses with `list` fields | `frozen` + `list` is only shallow immutability. Later cycles (command bus, undo/redo, optimistic revision) need real snapshots; `tuple` also makes hypothesis shrinking deterministic. The specs' word "list" is read as "ordered sequence" |
| DD4 | Rule registry = explicit static `RULES: tuple[Rule, ...]` in `engine.py`, importing named functions from `rules/` | `@rule` decorator auto-registry; entry-point/plugin discovery | Deterministic order, no import-time side effects, no hidden global mutable state, greppable, and the registry itself is assertable in a test ("exactly 10 rules") |
| DD5 | `validate(model, rules=RULES)` — registry injectable via default argument | Hard-coded registry; engine class with DI | Lets the aggregation/no-short-circuit behaviour be tested with fake rules without touching the real 10, while the public one-arg call stays exactly as specified |
| DD6 | Rules keep the exact `(CanonicalUmlModel) -> Iterable[Diagnostic]` signature and build their own local id→element dicts | Engine passes a shared prebuilt `ModelIndex` as a second parameter | Preserves the spec's "callable in isolation" requirement with zero setup. Class-diagram scale (tens of elements) makes repeated dict construction negligible; an optional second param can be added later without breaking callers |
| DD7 | Ids are `ElementId = NewType("ElementId", str)` (uuid4 hex) | `int`, `uuid.UUID`, or dataclass id objects | Strings serialize to JSON/XMI with no adapter; `NewType` gives static distinctness at zero runtime cost; ids are already the diagnostic `path` alphabet (D5) |
| DD8 | Pure mutation helpers take an explicit `now: datetime` argument | Calling `datetime.now(UTC)` inside the domain | Keeps the domain deterministic and clock-free; revision/timestamp tests need no freezegun or monkeypatching |
| DD9 | Diagnostic `code` is a `StrEnum` (`DiagnosticCode`), path builders live beside `Diagnostic` in `diagnostics.py` | Free-form `str` codes; separate `paths.py` | The 10 codes are fixed and closed, so an enum prevents typos and enables exhaustiveness tests; the `path` grammar is part of the diagnostic contract, so it belongs with it rather than in a fifth module |

## Module Layout (refined)

The proposal's layout is confirmed with two refinements:

1. **`validation/rules/structure.py` added** — `CLASS_WITHOUT_ATTRIBUTES` fits none of
   the four proposed rule files (naming/relationships/types/multiplicity).
2. **No `paths.py`** — path builders are colocated in `diagnostics.py` (DD9).

Rule-to-file mapping (each file is one independently testable unit for `sdd-tasks`):

| File | Rules |
|---|---|
| `rules/naming.py` | `EMPTY_ELEMENT_NAME`, `DUPLICATE_CLASS_NAME`, `DUPLICATE_ATTRIBUTE_NAME`, `DUPLICATE_ENUMERATION_LITERAL` |
| `rules/types.py` | `UNKNOWN_ATTRIBUTE_TYPE` |
| `rules/relationships.py` | `INVALID_RELATIONSHIP_ENDPOINT`, `GENERALIZATION_CYCLE`, `SELF_ASSOCIATION` |
| `rules/multiplicity.py` | `INVALID_MULTIPLICITY` |
| `rules/structure.py` | `CLASS_WITHOUT_ATTRIBUTES` |

`EMPTY_ELEMENT_NAME` is cross-cutting: one function walking every named element
(class, attribute, operation, enumeration, literal) via `model.iter_named_elements()`.

## Data Flow

```
caller (future: save / import / assistant / generation)
   │  validate(model)
   ▼
engine.validate ── for rule in RULES (declared order) ──▶ rule(model)
   │                                                        │
   │◀──────────── Iterable[Diagnostic] (never raises) ───────┘
   │  concatenate, no short-circuit
   ▼
ValidationResult(diagnostics=tuple)
   ├─ errors      = [d for d in diagnostics if d.severity is ERROR]
   └─ is_blocking = bool(errors)      # WARNING never blocks
```

Diagnostic order is fully deterministic: registry order × model declaration order.
Rules are total functions — a rule never raises; anything it cannot interpret is
reported as a diagnostic, so one broken element cannot suppress the other nine rules.

## Interfaces / Contracts

```python
# domain/ids.py
ElementId = NewType("ElementId", str)
def new_id() -> ElementId: ...                       # uuid4().hex

# domain/types.py
class PrimitiveType(StrEnum):                        # exactly 8 (D4)
    STRING; TEXT; INTEGER; LONG; DECIMAL; BOOLEAN; DATE; DATETIME
@dataclass(frozen=True) class EnumerationRef: enumeration_id: ElementId
AttributeType = PrimitiveType | EnumerationRef       # closed union (D2)
@dataclass(frozen=True) class Multiplicity: lower: int; upper: int | None   # unvalidated (DD2)
def parse_multiplicity(text: str) -> Multiplicity    # ValueError on malformed syntax only
def format_multiplicity(value: Multiplicity) -> str  # "1" | "0..1" | "0..*" | "1..*"

# domain/elements.py
class Visibility(StrEnum): PUBLIC; PRIVATE; PROTECTED; PACKAGE
class RelationshipKind(StrEnum): ASSOCIATION; AGGREGATION; COMPOSITION; GENERALIZATION
@dataclass(frozen=True) class UmlAttribute:
    id: ElementId; name: str; type: AttributeType; visibility: Visibility = PRIVATE
    # __post_init__ rejects any type outside the closed union (a class ref)
@dataclass(frozen=True) class UmlParameter: name: str; type: AttributeType
@dataclass(frozen=True) class UmlOperation:
    id; name; return_type: AttributeType | None = None
    parameters: tuple[UmlParameter, ...] = (); visibility: Visibility = PUBLIC
@dataclass(frozen=True) class UmlClass:
    id; name; attributes: tuple[UmlAttribute, ...] = (); operations: tuple[UmlOperation, ...] = ()
    visibility: Visibility = PUBLIC
@dataclass(frozen=True) class EnumerationLiteral: id; name: str; value: str | None = None
@dataclass(frozen=True) class Enumeration: id; name; literals: tuple[EnumerationLiteral, ...] = ()
@dataclass(frozen=True) class RelationshipEnd:
    class_id: ElementId; multiplicity: Multiplicity; role: str | None = None
@dataclass(frozen=True) class Relationship:
    id; kind: RelationshipKind; source: RelationshipEnd; target: RelationshipEnd; name: str | None = None
    # GENERALIZATION direction is normative: source = specific (child), target = general (parent)

# domain/model.py
@dataclass(frozen=True) class CanonicalUmlModel:
    classes: tuple[UmlClass, ...] = (); enumerations: tuple[Enumeration, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    generation_metadata: Mapping[ElementId, Mapping[str, object]] = EMPTY   # D8, opaque, unvalidated
    def class_by_id / enumeration_by_id / iter_named_elements(self): ...
UmlModel = CanonicalUmlModel                          # D0: alias, same object

# documents.py
@dataclass(frozen=True) class ProjectMetadata: name: str; description: str = ""
@dataclass(frozen=True) class Position: x: float; y: float
@dataclass(frozen=True) class DiagramLayout: positions: Mapping[ElementId, Position] = EMPTY
@dataclass(frozen=True) class ProjectDocument:
    id: UUID; metadata: ProjectMetadata; owner_id: str            # opaque, non-empty (D6)
    model: CanonicalUmlModel; layout: DiagramLayout
    revision: int = 1; created_at: datetime; updated_at: datetime
    def with_model(self, model, *, now: datetime) -> "ProjectDocument"    # revision + 1 (DD8)
    def with_layout(self, layout, *, now: datetime) -> "ProjectDocument"  # revision + 1

# validation/diagnostics.py
class Severity(StrEnum): ERROR; WARNING
class DiagnosticCode(StrEnum): ...                    # exactly the 10 D5 codes
class ElementKind(StrEnum): MODEL; CLASS; ATTRIBUTE; OPERATION; ENUMERATION; LITERAL; RELATIONSHIP
@dataclass(frozen=True) class ElementRef: kind: ElementKind; id: ElementId
@dataclass(frozen=True) class Diagnostic:
    severity: Severity; code: DiagnosticCode; message: str; path: str; element_ref: ElementRef | None
@dataclass(frozen=True) class ValidationResult:
    diagnostics: tuple[Diagnostic, ...]
    @property errors -> tuple[Diagnostic, ...]; @property is_blocking -> bool
def class_path(cid) / attribute_path(cid, aid) / operation_path(cid, oid) / \
    enumeration_path(eid) / literal_path(eid, lid) / relationship_path(rid) -> str

# validation/engine.py
Rule = Callable[[CanonicalUmlModel], Iterable[Diagnostic]]
RULES: tuple[Rule, ...] = (...)                       # 10 rules, declared order (DD4)
def validate(model: CanonicalUmlModel, rules: tuple[Rule, ...] = RULES) -> ValidationResult
```

**`GENERALIZATION_CYCLE` algorithm**: build the child→parent digraph from
`GENERALIZATION` relationships, run iterative DFS with a gray set, and emit **one**
diagnostic per detected cycle anchored at the lowest-sorted participating class id
(not one per member) so the count is deterministic. A self-generalization
(`source.class_id == target.class_id`, kind `GENERALIZATION`) is a length-1 cycle and
reports `GENERALIZATION_CYCLE` only; `SELF_ASSOCIATION` is scoped to kind
`ASSOCIATION` per its spec scenario.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/uml_modeling/__init__.py`, `apps.py` | Create | Registration shell; `name = "apps.uml_modeling"`, `label = "uml_modeling"` (`backend/apps/` is already a package) |
| `backend/apps/uml_modeling/domain/{__init__,ids,types,elements,model}.py` | Create | Pure domain (D0–D4, D8) |
| `backend/apps/uml_modeling/documents.py` | Create | `ProjectDocument`, `ProjectMetadata`, `DiagramLayout`, `Position` (D6) |
| `backend/apps/uml_modeling/validation/{__init__,diagnostics,engine}.py` | Create | Diagnostic contract + entry point + registry |
| `backend/apps/uml_modeling/validation/rules/{__init__,naming,types,relationships,multiplicity,structure}.py` | Create | The 10 rules |
| `backend/apps/uml_modeling/tests/**` | Create | One test module per domain/validation unit |
| `backend/config/settings.py` | Modify | Add `"apps.uml_modeling"` under the `# Local` marker in `INSTALLED_APPS` |
| `docs/ai/DECISIONS_LOG.md` | Modify | DD1–DD9 (this phase) + proposal D0–D8 |
| `docs/ai/CURRENT_STATE.md`, `ARCHITECTURE.md`, `NEXT_STEPS.md` | Modify | Real-state convention (sdd-apply) |

No `models.py`, no `migrations/`, no urlconf, no `schemas.py`, no new dependency.

## Testing Strategy

Strict TDD (RED→GREEN→REFACTOR), `pytest` only — no `pytest-django` DB fixtures.
`backend/pyproject.toml` already sets `testpaths = ["config", "apps"]`, so
`backend/apps/uml_modeling/tests/` is collected with zero configuration change.

| Layer | What to test | Approach |
|---|---|---|
| Unit — domain | Dataclass shapes, `UmlModel` alias identity, ordering preservation, construction rejections (class-typed attribute, empty `owner_id`), revision increment | Plain `pytest`, literal fixtures |
| Property — domain | `format(parse(s)) == s` over the 4 UML forms; `parse(format(m)) == m` over generated `Multiplicity` | `hypothesis` strategies |
| Unit — rules | One test module per rule file; each rule invoked **directly** (never via `validate`) asserting code, severity, `path`, `element_ref` | Minimal model per scenario, mirroring the spec's 11 scenarios |
| Unit — engine | Registry has exactly 10 rules; no short-circuit (two unrelated violations both present); `is_blocking` from ERROR only; aggregation tested with injected fake rules | `validate(model, rules=fakes)` (DD5) |
| Integration | Every emitted `path`/`element_ref` resolves to an element actually present in the model | Shared assertion helper reused across rule tests |
| E2E | N/A | No endpoint this cycle |

Test fixtures: a `tests/factories.py` builder (`a_class()`, `a_model()`, …) so each
scenario differs only in the violated fact — this is the main defence against the 11
rule scenarios becoming 11 hand-built models.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. This cycle adds pure in-process
dataclasses and functions with no I/O, no network, and no user-supplied code paths.

## Migration / Rollout

No migration required. No models, no DB tables, no persisted data, no API consumers.
Rollback = delete `backend/apps/uml_modeling/` and the single `INSTALLED_APPS` line.

## Sequence-Diagram Rule

`openspec/config.yaml` `rules.design` requires sequence diagrams for
realtime/collaboration flows (Django Channels). No realtime flow exists in this
cycle's scope (proposal Out of Scope, items 9–10), so the rule does not apply. The
`validate()` call-flow diagram above is included instead, as the only non-obvious
control flow in the change.

## Open Questions

- [ ] D7 (intra-backend imports permitted) remains flagged for user override. Nothing
      in Cycle 1 depends on it — one app ships — but it must be settled before a
      second backend app exists.
- [ ] `generation_metadata` value type is `Mapping[str, object]` (opaque per D8). If
      `sdd-apply` finds this unusable for typing, narrowing to `Mapping[str, str]` is
      additive-safe but should be recorded.
- [ ] `domain/types.py` and `rules/types.py` share a name with the stdlib `types`
      module. Absolute imports (Python 3 default) make this safe; noted so it is not
      "fixed" accidentally.
- [ ] `EMPTY_ELEMENT_NAME` on a whitespace-only name (`"  "`): treated as empty
      (`name.strip() == ""`). The spec only shows `name=""`; this is a deliberate
      superset — confirm at verify.

> Size note: this artifact exceeds the skill's 800-word soft budget because the
> orchestrator's completion criteria require field-level dataclass detail sufficient
> for `sdd-tasks` to slice implementable units. Completeness was prioritized, matching
> the same explicit tradeoff `sdd-spec` recorded for the 10-rule scenario table.
