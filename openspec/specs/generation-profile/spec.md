# Generation Profile Specification

## Purpose

Defines the generation profile vocabulary of spec section 33 (`entity, auditable, readOnly, searchable, crud, sortable, defaultSort`) as typed, frozen, hashable value objects carried by the relational mapper, and the strict parser that reads the reserved `"profile"` key of each `CanonicalUmlModel.generation_metadata[element_id]` entry. Undeclared intent is represented as `None`, never as an invented default (DD131, DD133). Lives in `apps.relational_mapping` (`domain/profile.py`, `mapping/profile_parser.py`, `mapping/errors.py`). Out of scope: Domain Manifest emission of profile fields, Spring filtering/search/sorting generation, any authoring path (commands, schemas, API, UI), the `required` / `unique` keys, `entity: false` semantics, resolving `defaultSort.attribute` to a column name, and provenance keys (`source`, `confidence`), which stay ignored.

Value-type note: section 33 fixes only the key set. The value types below (booleans, the `crud` subset, the `defaultSort` `{attribute, direction}` object, the `asc`/`desc` direction) are this project's own profile, resolved in the proposal; they are NOT a literal transcription of section 33 and MUST NOT be read as such.

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run.

## Requirements

### Requirement: Profile Value Objects

The system MUST provide, in `apps.relational_mapping.domain.profile`, the types `SortDirection` (`StrEnum`: `ASC = "asc"`, `DESC = "desc"`), `CrudOperation` (`StrEnum`: `CREATE`, `READ`, `UPDATE`, `DELETE` with values `create`, `read`, `update`, `delete`), and the frozen dataclasses `DefaultSort(attribute_id: ElementId, direction: SortDirection)`, `ColumnProfile(searchable, sortable, read_only)` and `TableProfile(entity, auditable, read_only, crud, default_sort)`. Every `ColumnProfile` and `TableProfile` field MUST be `X | None` with default `None`, where `None` means undeclared. `TableProfile.crud` MUST be `tuple[CrudOperation, ...] | None`, never a `set`, `frozenset` or `list`. All fields MUST be hashable types only. **[pytest]**

#### Scenario: All fields default to undeclared

- GIVEN `ColumnProfile()` and `TableProfile()`
- WHEN every field is read
- THEN every field is `None`

#### Scenario: Value objects are frozen

- GIVEN a `ColumnProfile(searchable=True)` and a `TableProfile(auditable=True)`
- WHEN a field is assigned on either instance
- THEN `dataclasses.FrozenInstanceError` is raised

#### Scenario: Equality and hashing are structural

- GIVEN two separately built `TableProfile` values with the same fields, including a `DefaultSort` and a `crud` tuple
- WHEN they are compared and hashed
- THEN they are equal, `hash()` succeeds and both hashes are equal, and `{p1} == {p2}` holds
- AND `hash(Column(..., profile=ColumnProfile(searchable=True)))` succeeds

#### Scenario: Module import purity

- GIVEN the source of `domain/profile.py` and `mapping/profile_parser.py`
- WHEN their imports are inspected with `ast`
- THEN neither imports `django`, `psycopg`, `sqlite3`, `MySQLdb`, `java` or `org.springframework`
- AND `profile_parser` additionally imports none of `apps.uml_modeling.domain.model`, `apps.domain_manifest`, `apps.spring_generator`

### Requirement: Profile Key Vocabulary and Levels

The parser MUST accept exactly these keys inside `"profile"`, by level (DD137): table level (class element id) `entity`, `auditable`, `readOnly`, `crud`, `defaultSort`; column level (attribute element id) `searchable`, `sortable`, `readOnly`. The levels MUST be disjoint except `readOnly`. A table-level key inside an attribute entry, or a column-level key inside a class entry, MUST be treated as an unknown key at that level. `aliases`, `required` and `unique` MUST NOT be profile keys (DD138). **[pytest]**

#### Scenario: Full table entry parses

- GIVEN a class entry `{"profile": {"entity": True, "auditable": True, "readOnly": False, "crud": ["read", "create"], "defaultSort": {"attribute": "attr-total", "direction": "desc"}}}`
- WHEN `parse_table_profile(element_id, entry)` runs
- THEN it returns `TableProfile(entity=True, auditable=True, read_only=False, crud=(CrudOperation.CREATE, CrudOperation.READ), default_sort=DefaultSort(ElementId("attr-total"), SortDirection.DESC))`

#### Scenario: Full column entry parses

- GIVEN an attribute entry `{"profile": {"searchable": True, "sortable": True, "readOnly": False}}`
- WHEN `parse_column_profile(element_id, entry)` runs
- THEN it returns `ColumnProfile(searchable=True, sortable=True, read_only=False)`

#### Scenario: Partial entries leave other keys undeclared

- GIVEN a class entry declaring only `auditable` and an attribute entry declaring only `sortable`
- WHEN each is parsed
- THEN the declared field holds its value and every other field is `None`

#### Scenario: Cross-level key raises

- GIVEN a class entry `{"profile": {"searchable": True}}` and an attribute entry `{"profile": {"crud": ["read"]}}`
- WHEN each is parsed
- THEN the first raises with reason `unknown table-level profile key` and the second raises with reason `unknown column-level profile key`

#### Scenario: `aliases`, `required` and `unique` are rejected inside profile

- GIVEN entries whose `"profile"` contains `aliases`, `required` or `unique`
- WHEN parsed
- THEN each raises `InvalidGenerationProfileError` for an unknown key at that level

### Requirement: None Means Undeclared

Every absent key MUST parse to `None`, per key and per element. A `"profile"` key that is absent, or present yielding zero declared keys (including `{}`), MUST canonicalize to `None` rather than an empty `ColumnProfile()` / `TableProfile()`. An entry containing only keys outside `"profile"` (for example `source`, `confidence`) MUST parse to `None`. A JSON `null` value for a profile key MUST NOT be treated as undeclared; it MUST raise (see Validation Rules). **[pytest]**

#### Scenario: Absent key stays None per key

- GIVEN an attribute entry declaring only `searchable: True`
- WHEN parsed
- THEN `sortable is None` and `read_only is None`, not `False`

#### Scenario: Zero declared keys canonicalizes to None

- GIVEN entries `{"profile": {}}`, `{}` and `{"source": "llm", "confidence": 0.9}`
- WHEN each is parsed at either level
- THEN every result is `None`, not an empty profile instance

#### Scenario: Undeclared element has no profile

- GIVEN a class and an attribute with no `generation_metadata` entry
- WHEN the model is mapped
- THEN the resulting `Table.profile` and `Column.profile` are `None`

### Requirement: Strict Validation Rules

Inside the reserved `"profile"` namespace the parser MUST raise `InvalidGenerationProfileError` on the first offending entry, with the exact `key` and `reason` below (`{value!r}` is the `repr` of the offending value, `{name!r}` of the missing key name). Boolean checks MUST use strict `isinstance(value, bool)`, so `1`, `0`, `"true"` and `None` all raise; CRUD membership MUST be exact-value, so `"READ"` raises. **[pytest]**

| # | Condition | `key` | `reason` |
|---|---|---|---|
| 1 | entry is not a `Mapping` | `None` | `metadata entry is not a mapping` |
| 2 | `entry["profile"]` is not a `Mapping` | `"profile"` | `expected an object` |
| 3 | key not in this level's set | the key | `unknown table-level profile key` / `unknown column-level profile key` |
| 4 | boolean key whose value fails `isinstance(v, bool)` | the key | `expected a boolean` |
| 5 | `crud` not a `list`/`tuple`, or a non-`str` member | `"crud"` | `expected a list of CRUD operations` |
| 6 | member outside the four operations | `"crud"` | `unknown CRUD operation {value!r}` |
| 7 | repeated member | `"crud"` | `duplicate CRUD operation {value!r}` |
| 8 | `defaultSort` not a `Mapping` | `"defaultSort"` | `expected an object with 'attribute' and 'direction'` |
| 9 | `attribute` or `direction` missing | `"defaultSort"` | `missing required key {name!r}` |
| 10 | unknown nested key | `"defaultSort.<key>"` | `unknown key` |
| 11 | `attribute` not a non-empty `str` | `"defaultSort.attribute"` | `expected a non-empty string` |
| 12 | `direction` not `"asc"`/`"desc"` | `"defaultSort.direction"` | `expected 'asc' or 'desc'` |

#### Scenario: Rule 1, entry is not a mapping

- GIVEN an entry `["profile"]` (a list) for element `e1`
- WHEN parsed
- THEN `InvalidGenerationProfileError` is raised with `key is None`, `reason == "metadata entry is not a mapping"` and `str(exc) == "Invalid generation profile for element 'e1': metadata entry is not a mapping"` (element id rendered by `{element_id!r}`)

#### Scenario: Rule 2, profile is not an object

- GIVEN an entry `{"profile": ["searchable"]}`
- WHEN parsed
- THEN it raises with `key == "profile"` and `reason == "expected an object"`

#### Scenario: Rule 3, unknown key

- GIVEN a class entry `{"profile": {"colour": True}}` and an attribute entry `{"profile": {"colour": True}}`
- WHEN each is parsed
- THEN each raises with `key == "colour"` and reasons `unknown table-level profile key` and `unknown column-level profile key` respectively

#### Scenario: Rule 4, boolean strictness

- GIVEN values `1`, `0`, `"true"` and `None` for `searchable` (column level) and for `auditable` (table level)
- WHEN parsed
- THEN every case raises with the key set to that key and `reason == "expected a boolean"`

#### Scenario: Rule 5, crud is not a list of strings

- GIVEN `crud` values `"read"`, `{"read": True}` and `["read", 1]`
- WHEN parsed
- THEN every case raises with `key == "crud"` and `reason == "expected a list of CRUD operations"`

#### Scenario: Rule 6, unknown CRUD operation

- GIVEN `crud: ["read", "READ"]`
- WHEN parsed
- THEN it raises with `key == "crud"` and `reason == "unknown CRUD operation 'READ'"`

#### Scenario: Rule 7, duplicate CRUD operation

- GIVEN `crud: ["read", "create", "read"]`
- WHEN parsed
- THEN it raises with `key == "crud"` and `reason == "duplicate CRUD operation 'read'"`

#### Scenario: Rule 8, defaultSort is not an object

- GIVEN `defaultSort: "attr-total"`
- WHEN parsed
- THEN it raises with `key == "defaultSort"` and `reason == "expected an object with 'attribute' and 'direction'"`

#### Scenario: Rule 9, defaultSort missing a required key

- GIVEN `defaultSort: {"direction": "asc"}` and `defaultSort: {"attribute": "a1"}`
- WHEN parsed
- THEN they raise with `key == "defaultSort"` and reasons `missing required key 'attribute'` and `missing required key 'direction'` respectively

#### Scenario: Rule 10, unknown nested defaultSort key

- GIVEN `defaultSort: {"attribute": "a1", "direction": "asc", "nulls": "first"}`
- WHEN parsed
- THEN it raises with `key == "defaultSort.nulls"` and `reason == "unknown key"`

#### Scenario: Rule 11, defaultSort attribute not a non-empty string

- GIVEN `defaultSort.attribute` equal to `""`, `5` and `None`
- WHEN parsed
- THEN every case raises with `key == "defaultSort.attribute"` and `reason == "expected a non-empty string"`

#### Scenario: Rule 12, defaultSort direction invalid

- GIVEN `defaultSort.direction` equal to `"ASC"`, `"up"` and `None`
- WHEN parsed
- THEN every case raises with `key == "defaultSort.direction"` and `reason == "expected 'asc' or 'desc'"`

#### Scenario: Error message with a key

- GIVEN a rule with a non-`None` key (for example rule 4 on `searchable` for element `a1`)
- WHEN the error is raised
- THEN `str(exc) == "Invalid generation profile for element 'a1', key 'searchable': expected a boolean"`
- AND `exc.element_id`, `exc.key` and `exc.reason` carry the offending element id, key and reason

#### Scenario: Error is an UnmappableModelError

- GIVEN any `InvalidGenerationProfileError`
- WHEN it is caught as `UnmappableModelError`
- THEN the catch succeeds (DD136)

### Requirement: CRUD Canonical Ordering

A valid `crud` list MUST be parsed to a tuple in the canonical order `create, read, update, delete`, regardless of input order (DD134). An empty `crud` list MUST parse to an empty tuple (a declared, empty subset), distinct from `None`. **[pytest]**

#### Scenario: Input order does not matter

- GIVEN `crud: ["delete", "read", "create"]` and `crud: ["create", "read", "delete"]`
- WHEN each is parsed
- THEN both yield `(CrudOperation.CREATE, CrudOperation.READ, CrudOperation.DELETE)` and the two `TableProfile` values are equal with equal hashes

#### Scenario: Empty crud list is declared

- GIVEN `crud: []`
- WHEN parsed
- THEN the table profile has `crud == ()`, not `None`

### Requirement: defaultSort Is Stored Unresolved

`DefaultSort.attribute_id` MUST hold the raw `ElementId` from `defaultSort.attribute`. The parser MUST NOT look up the attribute; an id matching no attribute MUST NOT be an error in this capability (DD140). **[pytest]**

#### Scenario: Unresolvable attribute id is accepted

- GIVEN `defaultSort: {"attribute": "no-such-attribute", "direction": "asc"}`
- WHEN parsed and mapped
- THEN `default_sort == DefaultSort(ElementId("no-such-attribute"), SortDirection.ASC)` and no error is raised

### Requirement: Entity Key Is Carried, Not Acted On

`entity` MUST be accepted as a boolean and stored in `TableProfile.entity`. No mapper behaviour MUST branch on it (DD139). **[pytest]**

#### Scenario: entity false does not change mapping

- GIVEN a class with `{"profile": {"entity": False}}`
- WHEN the model is mapped
- THEN the class still produces its `Table`, with `Table.profile.entity is False`

### Requirement: Keys Outside profile and Unknown Element Ids Are Ignored

Strictness MUST apply only inside the reserved `"profile"` namespace. Keys of an entry outside `"profile"` (for example `source`, `confidence`, `aliases`) MUST be ignored without validation. A `generation_metadata` element id that matches neither a class id nor an attribute id MUST be skipped without validation and MUST NOT raise, even if its entry is malformed (DD138). **[pytest]**

#### Scenario: Provenance keys are ignored

- GIVEN an entry `{"source": "llm", "confidence": "not-a-number", "aliases": 7, "profile": {"auditable": True}}`
- WHEN parsed
- THEN only `auditable` is read and no error is raised for the other keys

#### Scenario: Unknown element id is skipped

- GIVEN a `generation_metadata` entry keyed by an id that is neither a class nor an attribute, whose value is `"garbage"`
- WHEN the model is mapped
- THEN mapping succeeds and no `Table.profile` or `Column.profile` reflects that entry

### Requirement: Parser Purity and Determinism

`parse_table_profile(element_id, entry)` and `parse_column_profile(element_id, entry)` MUST be pure, model-free functions of one raw entry: no I/O, no clock, no environment, no import of the UML model (DD135). The same input MUST always produce an equal, equally hashed result. **[pytest]**

#### Scenario: Same entry, equal result

- GIVEN one raw entry parsed twice
- WHEN the results are compared
- THEN they are `==` and `hash()` values are equal

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
## Verification Commands

- `docker compose exec -T backend pytest -q apps/relational_mapping` **[pytest]**
- `docker compose exec -T backend pytest -q` (full suite) **[pytest]**
