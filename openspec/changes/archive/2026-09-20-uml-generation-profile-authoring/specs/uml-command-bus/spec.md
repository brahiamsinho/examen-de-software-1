# UML Command Bus Delta: Generation Profile Authoring

Delta against `openspec/specs/uml-command-bus/spec.md`. Requirements not listed here (Dispatcher Apply Contract, AddClass, RenameClass, AddAttribute, AddRelationship, RemoveRelationship, Always-Apply Diagnostics Policy, Missing-Target No-Op Policy, `uml_commands Import Boundary`, AddOperation, RemoveOperation) are unchanged; in particular the `uml_commands Import Boundary` requirement and its guard test are NOT touched (the new handler imports only `apps.uml_modeling` and the standard library, DD152). Profile vocabulary and parse rules are specified in `generation-profile`; write-time validation is specified in `uml-document-persistence`. Design decisions: DD151-DD159 (`design.md`).

Verification key: **[pytest]** = automated in the default suite; **[manual]** = verified by a recorded gate run.

## ADDED Requirements

### Requirement: SetGenerationProfile

`apps.uml_commands.commands` MUST define a frozen dataclass `SetGenerationProfile(element_id: ElementId, profile: Mapping[str, object] | None = None)` and MUST add it as the LAST member of the `UmlCommand` union. `profile` carries the raw JSON-native mapping as received (DD152); the command module MUST NOT import `apps.relational_mapping`. The dispatcher MUST register `SetGenerationProfile` in `_HANDLERS` to `apps.uml_commands.handlers.generation_profile.set_generation_profile`, so `apply()` returns a `CommandResult` whose document revision is exactly one greater than the input's and whose `validation_result` equals `validate(new_model, rules=RULES)` (Dispatcher Apply Contract unchanged).

`set_generation_profile(model, command)` MUST be purely structural and MUST NEVER raise (DD6). It MUST own exactly the `"profile"` key of `model.generation_metadata[element_id]` (DD156) and MUST evaluate, in order:

| # | Condition | Result |
|---|---|---|
| 1 | `element_id` is neither a class id nor an attribute id of any class | return `model` **unchanged** (DD6), no raise |
| 2 | `command.profile` is truthy (a non-empty mapping) | `entry["profile"] = dict(command.profile)`, every sibling key preserved |
| 3 | `command.profile` is `None` or `{}` | `entry.pop("profile", None)` |
| 4 | the resulting `entry` is empty | drop `metadata[element_id]` entirely |
| 5 | the resulting metadata equals the input | return `model` unchanged (no `dataclasses.replace`) |

The handler MUST NOT touch `classes`, `enumerations`, or `relationships`, and MUST NOT mutate the input model or its metadata mapping. Sibling keys of the entry (for example `source`, `confidence`, or any key other than `"profile"`) MUST be preserved byte-for-byte. Semantic validation of the profile body is NOT the handler's responsibility (it belongs to the write path, see `uml-document-persistence`). **[pytest]**

#### Scenario: Setting a profile on a class id stores it under the "profile" key

- GIVEN a model with class C and empty `generation_metadata`
- WHEN `SetGenerationProfile(C.id, {"auditable": true, "crud": ["create", "read"]})` is applied
- THEN `generation_metadata[C.id] == {"profile": {"auditable": true, "crud": ["create", "read"]}}`
- AND `classes`, `enumerations`, and `relationships` are unchanged **[pytest]**

#### Scenario: Setting a profile on an attribute id stores it under the "profile" key

- GIVEN a model with class C owning attribute A and empty `generation_metadata`
- WHEN `SetGenerationProfile(A.id, {"searchable": true})` is applied
- THEN `generation_metadata[A.id] == {"profile": {"searchable": true}}` **[pytest]**

#### Scenario: Sibling metadata keys are preserved when setting a profile

- GIVEN `generation_metadata[C.id] == {"source": "ai", "confidence": 0.9}`
- WHEN `SetGenerationProfile(C.id, {"auditable": true})` is applied
- THEN `generation_metadata[C.id] == {"source": "ai", "confidence": 0.9, "profile": {"auditable": true}}` **[pytest]**

#### Scenario: Setting a profile replaces a previous profile wholesale

- GIVEN `generation_metadata[C.id] == {"profile": {"auditable": true, "readOnly": true}}`
- WHEN `SetGenerationProfile(C.id, {"crud": ["read"]})` is applied
- THEN `generation_metadata[C.id] == {"profile": {"crud": ["read"]}}` **[pytest]**

#### Scenario: A None profile removes only the "profile" key

- GIVEN `generation_metadata[C.id] == {"source": "ai", "profile": {"auditable": true}}`
- WHEN `SetGenerationProfile(C.id, None)` is applied
- THEN `generation_metadata[C.id] == {"source": "ai"}` **[pytest]**

#### Scenario: An empty mapping profile clears exactly like None

- GIVEN `generation_metadata[C.id] == {"source": "ai", "profile": {"auditable": true}}`
- WHEN `SetGenerationProfile(C.id, {})` is applied
- THEN `generation_metadata[C.id] == {"source": "ai"}` **[pytest]**

#### Scenario: The entry is pruned when the profile was its only key

- GIVEN `generation_metadata == {C.id: {"profile": {"auditable": true}}}`
- WHEN `SetGenerationProfile(C.id, None)` is applied
- THEN `generation_metadata` has no entry for `C.id` (no `{}` residue) **[pytest]**

#### Scenario: A sibling-only entry survives a clear

- GIVEN `generation_metadata == {C.id: {"source": "ai"}}` and no `"profile"` key
- WHEN `SetGenerationProfile(C.id, None)` is applied
- THEN `generation_metadata[C.id] == {"source": "ai"}` **[pytest]**

#### Scenario: An unknown element id is a no-op that never raises

- GIVEN a model with no class or attribute matching id X
- WHEN `SetGenerationProfile(X, {"auditable": true})` and `SetGenerationProfile(X, None)` are each applied
- THEN each resulting model's content equals the input's, `generation_metadata` gains no entry for X, and the revision is exactly one greater than the input's
- AND no exception is raised **[pytest]**

#### Scenario: The input model is never mutated

- GIVEN a model whose `generation_metadata` has an entry for C
- WHEN any `SetGenerationProfile` is applied to C
- THEN the original model instance and its `generation_metadata` mapping are unchanged **[pytest]**

#### Scenario: The command is registered and bumps the revision

- GIVEN a `ProjectDocument` at revision N
- WHEN `apply(document, SetGenerationProfile(C.id, {"auditable": true}))` is called
- THEN the returned `CommandResult.document.revision` is N + 1 and `validation_result` equals `validate(new_model, rules=RULES)` **[pytest]**

### Requirement: Generation Metadata Pruning Primitive

`apps.uml_commands.handlers.generation_profile` MUST expose `prune_generation_metadata(metadata: Mapping[ElementId, Mapping[str, object]], removed_ids: frozenset[ElementId]) -> Mapping[ElementId, Mapping[str, object]]`, shared by the `RemoveClass` and `RemoveAttribute` handlers (DD158). It MUST apply these rules, structurally and without ever raising:

| # | Rule |
|---|---|
| 1 | drop every entry whose key is in `removed_ids` |
| 2 | on every surviving entry, if `entry["profile"]["defaultSort"]["attribute"]` is a `str` whose `ElementId` is in `removed_ids`, pop `"defaultSort"` |
| 3 | if `"profile"` became empty, pop `"profile"`; if the entry became empty, drop the entry |
| 4 | any non-`Mapping` shape encountered on the way down is left untouched — structural only, never raises |
| 5 | return the **same object** when nothing changed, so callers can skip `dataclasses.replace` |

Entries keyed by a relationship id or an operation id MUST NOT be pruned by this primitive or by any remove handler (DD159). **[pytest]**

#### Scenario: Entries keyed by a removed id are dropped

- GIVEN `metadata == {A: {"profile": {"searchable": true}}, B: {"profile": {"auditable": true}}}` and `removed_ids == frozenset({A})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the result is `{B: {"profile": {"auditable": true}}}` **[pytest]**

#### Scenario: A defaultSort pointing at a removed attribute is cleared

- GIVEN `metadata == {C: {"profile": {"auditable": true, "defaultSort": {"attribute": "attr-1", "direction": "asc"}}}}` and `removed_ids == frozenset({ElementId("attr-1")})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the result is `{C: {"profile": {"auditable": true}}}` **[pytest]**

#### Scenario: Empty containers left by pruning are removed

- GIVEN `metadata == {C: {"profile": {"defaultSort": {"attribute": "attr-1", "direction": "asc"}}}}` and `removed_ids == frozenset({ElementId("attr-1")})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN `"profile"` is popped because `defaultSort` was its only key, and the entry for `C` is dropped because `"profile"` was its only key, so the result is `{}` **[pytest]**

#### Scenario: Sibling keys survive when the profile is emptied

- GIVEN `metadata == {C: {"source": "ai", "profile": {"defaultSort": {"attribute": "attr-1", "direction": "asc"}}}}` and `removed_ids == frozenset({ElementId("attr-1")})`
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the result is `{C: {"source": "ai"}}` **[pytest]**

#### Scenario: Non-Mapping shapes are left untouched and never raise

- GIVEN entries whose `"profile"` is a list, whose `defaultSort` is a string, or whose `defaultSort.attribute` is an integer
- WHEN `prune_generation_metadata` is called with any `removed_ids`
- THEN no exception is raised and those entries are returned untouched **[pytest]**

#### Scenario: A no-change prune returns the same object

- GIVEN `metadata` with no entry keyed by, or `defaultSort`-referencing, any id in `removed_ids` (including empty `metadata`)
- WHEN `prune_generation_metadata(metadata, removed_ids)` is called
- THEN the returned object `is` the input `metadata` **[pytest]**

## MODIFIED Requirements

### Requirement: RemoveClass with Cascade

Applying `RemoveClass` MUST remove the matching `UmlClass` from
`model.classes` and MUST cascade-remove every `Relationship` whose `source`
or `target` `class_id` references the removed class, so no dangling
endpoint remains. It MUST also prune `model.generation_metadata` through the
shared `prune_generation_metadata` primitive (DD158), with `removed_ids` equal
to `{class_id}` plus the id of every attribute of the removed class: the entry
keyed by the class id and each entry keyed by one of its attribute ids MUST be
removed, and any *other* entry whose `profile.defaultSort.attribute` is one of
those removed attribute ids MUST have its `defaultSort` cleared (an inheritance
root's `defaultSort` may legitimately point at a descendant's attribute,
DD157). Entries keyed by relationship ids or operation ids MUST be left
untouched (DD159). When the target class is absent the handler MUST remain a
no-op (Missing-Target No-Op Policy). Removing a class that has no metadata
entries MUST leave `generation_metadata` the same object.
(Previously: `RemoveClass` only removed the class and its referencing
relationships and left `generation_metadata` entries for the class and its
attributes behind.)

#### Scenario: Class is removed

- GIVEN a model containing class C among others
- WHEN `RemoveClass(C.id)` is applied
- THEN the resulting model's `classes` no longer contains C
- AND all other classes, enumerations, and relationships are unchanged

#### Scenario: Referencing relationships are cascade-removed

- GIVEN classes A and B and a `Relationship` R with `source.class_id == A.id`
- WHEN `RemoveClass(A.id)` is applied
- THEN the resulting model's `classes` no longer contains A
- AND the resulting model's `relationships` no longer contains R
- AND `validate()` on the result reports no `INVALID_RELATIONSHIP_ENDPOINT` for R

#### Scenario: The class entry and its attribute entries are pruned

- GIVEN class C owning attributes A1 and A2, and `generation_metadata` entries keyed by `C.id`, `A1.id`, `A2.id`, and an unrelated class D
- WHEN `RemoveClass(C.id)` is applied
- THEN the resulting `generation_metadata` contains only the entry for D **[pytest]**

#### Scenario: A root's defaultSort on a removed descendant attribute is cleared

- GIVEN root class R and descendant class S (a `GENERALIZATION` from S to R) owning attribute SA, and `generation_metadata[R.id] == {"profile": {"auditable": true, "defaultSort": {"attribute": SA.id, "direction": "asc"}}}`
- WHEN `RemoveClass(S.id)` is applied
- THEN `generation_metadata[R.id] == {"profile": {"auditable": true}}`, so no `defaultSort` dangles **[pytest]**

#### Scenario: Relationship- and operation-keyed entries are not pruned

- GIVEN `generation_metadata` entries keyed by a relationship id and an operation id of class C
- WHEN `RemoveClass(C.id)` is applied
- THEN those two entries remain in the resulting `generation_metadata` byte-identical **[pytest]**

#### Scenario: Removing a class without metadata leaves generation_metadata untouched

- GIVEN a model whose `generation_metadata` has no entry keyed by C or its attributes and no `defaultSort` referencing them
- WHEN `RemoveClass(C.id)` is applied
- THEN the resulting model's `generation_metadata` is the same object as the input's **[pytest]**

### Requirement: RemoveAttribute

Applying `RemoveAttribute` MUST remove the matching `UmlAttribute` from the
target class's `attributes` tuple, preserving the relative order of the rest.
It MUST also prune `model.generation_metadata` through the shared
`prune_generation_metadata` primitive (DD158) with `removed_ids ==
{attribute_id}`: the entry keyed by the attribute id MUST be removed, and any
entry whose `profile.defaultSort.attribute` equals the removed attribute id
MUST have its `defaultSort` cleared, so no `defaultSort` dangles. Entries keyed
by relationship ids or operation ids MUST be left untouched (DD159). When the
target class or attribute is absent the handler MUST remain a no-op
(Missing-Target No-Op Policy).
(Previously: `RemoveAttribute` only removed the attribute and left its
`generation_metadata` entry, and any `defaultSort` pointing at it, behind.)

#### Scenario: Attribute is removed

- GIVEN class C with attributes including Attr
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN C's resulting `attributes` no longer contains Attr
- AND the remaining attributes keep their original relative order

#### Scenario: The attribute's metadata entry is pruned

- GIVEN class C with attribute Attr and `generation_metadata` entries keyed by `Attr.id` and by another attribute of C
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN the resulting `generation_metadata` has no entry for `Attr.id` and still has the other attribute's entry **[pytest]**

#### Scenario: The owning class's defaultSort pointing at the attribute is cleared

- GIVEN `generation_metadata[C.id] == {"profile": {"crud": ["read"], "defaultSort": {"attribute": Attr.id, "direction": "desc"}}}`
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN `generation_metadata[C.id] == {"profile": {"crud": ["read"]}}` **[pytest]**

#### Scenario: Unrelated entries are untouched

- GIVEN `generation_metadata` entries for class D and for an unrelated attribute, plus a `defaultSort` pointing at a different attribute
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN those entries are byte-identical in the resulting model **[pytest]**

#### Scenario: Removing an attribute without metadata leaves generation_metadata untouched

- GIVEN a model whose `generation_metadata` is empty
- WHEN `RemoveAttribute(C.id, Attr.id)` is applied
- THEN the resulting model's `generation_metadata` is the same object as the input's **[pytest]**
