# Generation Profile Delta: Effective Operations Derivation

Delta against `openspec/specs/generation-profile/spec.md`. Existing requirements are unchanged. The capability Purpose needs no edit: emission of operations stays owned by `domain-manifest-export`; this delta only adds the single pure derivation both the manifest and (in slice 2) the Spring generator consume. Design decisions: DD160-DD162 (`design.md`).

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run.

## ADDED Requirements

### Requirement: Effective Operations Derivation

`apps.relational_mapping.domain.profile` MUST expose the public constant `OPERATION_NAMES: tuple[str, ...] == ("create", "findById", "update", "delete", "list", "count")` (the six controller operation names in the controller's own declaration order) and the pure function `effective_operations(profile: TableProfile | None) -> tuple[str, ...]`. The function MUST map each declared `crud` member to controller names (`create` -> `create`; `read` -> `findById`, `list`, `count`; `update` -> `update`; `delete` -> `delete`); MUST treat `crud is None` (and `profile is None`, and `TableProfile()`) as all six operations; MUST, when `read_only is True`, intersect the result with `{findById, list, count}` (it never adds an operation); MUST treat `read_only` `False` or `None` as not restricting, so `crud` alone decides; and MUST return a plain `tuple[str, ...]` in `OPERATION_NAMES` order regardless of the declared `crud` order. An empty tuple is reachable exactly two ways: a declared empty `crud`, or `read_only=True` with a `crud` containing no `READ`. The function MUST NOT reject `read_only=True` combined with a write `crud` (silent fail-closed intersection; no parse-time error). The module MUST gain no new import, so the existing `Module import purity` scenario keeps covering it unchanged.

`apps.relational_mapping.domain.schema.Table` MUST expose `effective_operations` as a read-only **property** (not a method, not a dataclass field) that returns `effective_operations(self.profile)`, so `__eq__` and `repr` of the frozen `Table` are unchanged (`Table` remains unhashable because of its dict-typed field; the property does not alter that). **[pytest]**

The complete truth table (exhaustive; `crud` rows by `read_only` columns):

| `crud` | `read_only` `None` / `False` | `read_only` `True` |
|---|---|---|
| `None` (or `profile is None`) | `("create","findById","update","delete","list","count")` | `("findById","list","count")` |
| `()` | `()` | `()` |
| `(CREATE,)` | `("create",)` | `()` |
| `(READ,)` | `("findById","list","count")` | `("findById","list","count")` |
| `(UPDATE,)` | `("update",)` | `()` |
| `(DELETE,)` | `("delete",)` | `()` |
| `(CREATE, READ)` | `("create","findById","list","count")` | `("findById","list","count")` |
| `(CREATE, UPDATE, DELETE)` | `("create","update","delete")` | `()` |
| `(CREATE, READ, UPDATE, DELETE)` | all six | `("findById","list","count")` |

#### Scenario: Undeclared profile yields all six

- GIVEN `profile` is `None`, and separately `profile` is `TableProfile()`, and separately `TableProfile(auditable=True)` (no `crud`, no `read_only`)
- WHEN `effective_operations(profile)` is called for each
- THEN each result equals `("create", "findById", "update", "delete", "list", "count")` and equals `OPERATION_NAMES` **[pytest]**

#### Scenario: Declared crud maps to operation names

- GIVEN `read_only` is `None` and `crud` is each of `(CREATE,)`, `(READ,)`, `(UPDATE,)`, `(DELETE,)`, `(CREATE, READ)`, `(CREATE, UPDATE, DELETE)` and `(CREATE, READ, UPDATE, DELETE)`
- WHEN `effective_operations` is called for each
- THEN the results are, respectively, `("create",)`, `("findById","list","count")`, `("update",)`, `("delete",)`, `("create","findById","list","count")`, `("create","update","delete")` and all six, exactly as in the `read_only` `None` / `False` column of the truth table **[pytest]**

#### Scenario: readOnly true intersects the declared crud

- GIVEN `read_only=True` with `crud` equal to `None`, `(CREATE, READ)` and `(CREATE,)` respectively
- WHEN `effective_operations` is called for each
- THEN the results are `("findById","list","count")`, `("findById","list","count")` and `()` respectively, and no result ever contains `create`, `update` or `delete` **[pytest]**

#### Scenario: readOnly true with a write-only crud is empty without an error

- GIVEN `read_only=True` with `crud` equal to `(UPDATE,)`, `(DELETE,)` and `(CREATE, UPDATE, DELETE)`
- WHEN `effective_operations` is called for each
- THEN each returns `()` and no exception is raised (no parse-time rejection, silent intersection) **[pytest]**

#### Scenario: readOnly false or None lets crud decide

- GIVEN `crud=(CREATE, UPDATE)` and `read_only` set to `False`, then `None`
- WHEN `effective_operations` is called for each
- THEN both results equal `("create", "update")` and are equal to each other **[pytest]**

#### Scenario: Declared empty crud yields no operation

- GIVEN `TableProfile(crud=())`, both with `read_only=None` and with `read_only=True`
- WHEN `effective_operations` is called
- THEN the result is `()` in both cases, and it is distinct from the undeclared case (`crud=None`), which yields all six **[pytest]**

#### Scenario: Order is canonical and deterministic

- GIVEN `crud` declared as `(DELETE, CREATE, READ)` and, separately, as `(CREATE, READ, DELETE)`
- WHEN `effective_operations` is called twice on each
- THEN all four results are equal to `("create", "findById", "delete", "list", "count")`, the declared order has no effect, and every member satisfies `type(name) is str` and the result satisfies `type(result) is tuple` **[pytest]**

#### Scenario: Constant matches the controller declaration order

- GIVEN `OPERATION_NAMES`
- WHEN it is compared with the controller's own operation order
- THEN it equals `("create", "findById", "update", "delete", "list", "count")` and equals `tuple(name for name, *_ in domain_manifest.builder.entities._OPERATIONS)` (cross-app equality asserted by a test, which MAY import both modules; only `builder/**` is import-guarded) **[pytest]**

#### Scenario: Table exposes its effective operations

- GIVEN a `Table` whose `profile` is `None`, and a `Table` whose `profile` is `TableProfile(crud=(CrudOperation.READ,))`
- WHEN `table.effective_operations` is read (attribute access, no call)
- THEN the first equals `OPERATION_NAMES` and the second equals `("findById","list","count")`, each equal to `effective_operations(table.profile)` **[pytest]**

#### Scenario: The Table property is not a field

- GIVEN the frozen `Table` dataclass before and after the property is added
- WHEN `dataclasses.fields(Table)` is inspected and two `Table` instances with equal fields are compared
- THEN `effective_operations` is not among the fields, the two instances compare `==` with equal fields and equal `repr` (`Table` itself is unhashable because of a dict-typed field, so no hash equality is claimed), and `repr(table)` does not contain `effective_operations` **[pytest]**

#### Scenario: Derivation is pure

- GIVEN `effective_operations` and a `TableProfile`
- WHEN the function is called repeatedly with the same profile and the module `apps.relational_mapping.domain.profile` is scanned for imports
- THEN it reads no clock, environment or filesystem, does not mutate the profile, returns equal results on every call, and the module imports no Django, `apps.*` or driver module beyond what the existing `Module import purity` scenario already allows **[pytest]**
