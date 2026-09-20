"""The pure `map_to_relational` pipeline (spec §21, design.md Data Flow).

Never calls `validate()` (DD18): the mapper is a pure function of its
argument. It raises `UnmappableModelError` subclasses only as
defense-in-depth for the four structures it cannot represent — callers
validate before mapping; the `MULTI_PARENT_GENERALIZATION` and
`GENERALIZATION_CYCLE` rules (`apps.uml_modeling`) are the primary
enforcement.

Phase 2 implements Stage 1 (`_build_hierarchy`) plus the dangling
endpoint guard. Stages 2-5 (enumerations, tables, relationships,
freeze) are added in later phases of the same pipeline.
"""
from collections import defaultdict
from dataclasses import dataclass, field
from types import MappingProxyType

from apps.relational_mapping.domain.profile import ColumnProfile, TableProfile
from apps.relational_mapping.domain.schema import (
    Column,
    EnumType,
    ForeignKey,
    Index,
    PrimaryKey,
    RelationalModel,
    Table,
    UniqueConstraint,
)
from apps.relational_mapping.domain.types import ColumnType, ReferentialAction
from apps.relational_mapping.mapping.errors import (
    DanglingRelationshipEndpointError,
    GeneralizationCycleError,
    MultipleGeneralizationParentsError,
    UnknownEnumerationError,
)
from apps.relational_mapping.mapping.naming import snake_case, unique_name
from apps.relational_mapping.mapping.profile_parser import (
    parse_column_profile,
    parse_table_profile,
)
from apps.uml_modeling.domain.elements import (
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
)
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity, PrimitiveType

# Type mapping table (design.md "Type mapping table (DD10 + attribute -> column)").
_PRIMITIVE_TYPE_MAP: dict[PrimitiveType, tuple[ColumnType, dict[str, int]]] = {
    PrimitiveType.STRING: (ColumnType.VARCHAR, {"length": 255}),
    PrimitiveType.TEXT: (ColumnType.TEXT, {}),
    PrimitiveType.INTEGER: (ColumnType.INTEGER, {}),
    PrimitiveType.LONG: (ColumnType.BIGINT, {}),
    PrimitiveType.DECIMAL: (ColumnType.NUMERIC, {"precision": 19, "scale": 4}),
    PrimitiveType.BOOLEAN: (ColumnType.BOOLEAN, {}),
    PrimitiveType.DATE: (ColumnType.DATE, {}),
    PrimitiveType.DATETIME: (ColumnType.TIMESTAMPTZ, {}),
}


@dataclass
class _TableDraft:
    """Mutable builder frozen into a `Table` by `_freeze` (design.md DD3):
    FK columns are discovered in a later pass (Stage 4) than attribute
    columns (Stage 3), so a builder keeps the pipeline linear while the
    public output stays fully frozen.
    """

    name: str
    columns: list[Column] = field(default_factory=list)
    column_names: set[str] = field(default_factory=set)
    primary_key: PrimaryKey | None = None
    foreign_keys: list = field(default_factory=list)
    unique_constraints: list = field(default_factory=list)
    indexes: list = field(default_factory=list)
    source_class_ids: tuple[ElementId, ...] = ()
    discriminator_column: str | None = None
    discriminator_values: dict[ElementId, str] = field(default_factory=dict)
    profile: TableProfile | None = None


def _collect_profiles(
    model: CanonicalUmlModel,
    class_by_id: dict[ElementId, UmlClass],
    attribute_owner_by_id: dict[ElementId, ElementId],
) -> tuple[dict[ElementId, TableProfile], dict[ElementId, ColumnProfile]]:
    """DD141: parse every declared profile up front, in `generation_metadata`
    order, so the first malformed entry aborts the mapping deterministically.
    Ids matching neither a class nor an attribute are skipped unvalidated.
    """
    table_profile_by_id: dict[ElementId, TableProfile] = {}
    column_profile_by_id: dict[ElementId, ColumnProfile] = {}
    for element_id, entry in model.generation_metadata.items():
        if element_id in class_by_id:
            table_profile = parse_table_profile(element_id, entry)
            if table_profile is not None:
                table_profile_by_id[element_id] = table_profile
        elif element_id in attribute_owner_by_id:
            column_profile = parse_column_profile(element_id, entry)
            if column_profile is not None:
                column_profile_by_id[element_id] = column_profile
    return table_profile_by_id, column_profile_by_id


def _check_dangling_endpoints(model: CanonicalUmlModel) -> None:
    """Raise `DanglingRelationshipEndpointError` for the first
    relationship whose source or target id does not match any class in
    the model. Runs before hierarchy build so a dangling generalization
    target can never poison `parent_of`.
    """
    known_class_ids = {uml_class.id for uml_class in model.classes}
    for relationship in model.relationships:
        if (
            relationship.source.class_id not in known_class_ids
            or relationship.target.class_id not in known_class_ids
        ):
            raise DanglingRelationshipEndpointError(relationship.id)


def _build_hierarchy(
    model: CanonicalUmlModel,
) -> tuple[tuple[ElementId, ...], dict[ElementId, tuple[ElementId, ...]], dict[ElementId, ElementId]]:
    """Stage 1: `(roots, descendants_of, parent_of)`.

    `GENERALIZATION` direction is normative: `source` is the child,
    `target` is the parent (`domain/elements.py::Relationship`).
    `descendants_of[root]` is breadth-first, `model.classes` order
    (DD9). Raises `MultipleGeneralizationParentsError` when a class has
    more than one *distinct* parent (a duplicate edge to the same
    parent is not multiple inheritance), and `GeneralizationCycleError`
    when the child->parent digraph contains a cycle — without this
    guard the root walk on a cyclic model would not terminate.
    """
    parents_of: dict[ElementId, list[ElementId]] = defaultdict(list)
    for relationship in model.relationships:
        if relationship.kind is not RelationshipKind.GENERALIZATION:
            continue
        child = relationship.source.class_id
        parent = relationship.target.class_id
        if parent not in parents_of[child]:
            parents_of[child].append(parent)

    parent_of: dict[ElementId, ElementId] = {}
    for child, parents in parents_of.items():
        if len(parents) > 1:
            raise MultipleGeneralizationParentsError(child, tuple(parents))
        parent_of[child] = parents[0]

    cycle = _find_generalization_cycle(model, parent_of)
    if cycle is not None:
        raise GeneralizationCycleError(cycle)

    class_ids_in_order = [uml_class.id for uml_class in model.classes]

    children_of: dict[ElementId, list[ElementId]] = defaultdict(list)
    for class_id in class_ids_in_order:
        parent = parent_of.get(class_id)
        if parent is not None:
            children_of[parent].append(class_id)

    roots = tuple(class_id for class_id in class_ids_in_order if class_id not in parent_of)
    descendants_of = {root: _descendants_breadth_first(root, children_of) for root in roots}

    return roots, descendants_of, parent_of


def _find_generalization_cycle(
    model: CanonicalUmlModel, parent_of: dict[ElementId, ElementId]
) -> tuple[ElementId, ...] | None:
    """Walk each class's parent chain; a repeated node within the
    current walk is a cycle. A self-generalization (`parent_of[x] == x`)
    is a length-1 cycle, matching `uml_modeling`'s own rule.
    """
    visited: set[ElementId] = set()
    for uml_class in model.classes:
        start = uml_class.id
        if start in visited:
            continue
        path: list[ElementId] = []
        in_path: set[ElementId] = set()
        node: ElementId | None = start
        while node is not None:
            if node in in_path:
                cycle_start = path.index(node)
                return tuple(path[cycle_start:])
            if node in visited:
                break
            in_path.add(node)
            path.append(node)
            node = parent_of.get(node)
        visited.update(path)
    return None


def _descendants_breadth_first(
    root: ElementId, children_of: dict[ElementId, list[ElementId]]
) -> tuple[ElementId, ...]:
    result: list[ElementId] = []
    queue: list[ElementId] = list(children_of.get(root, ()))
    while queue:
        next_level: list[ElementId] = []
        for node in queue:
            result.append(node)
            next_level.extend(children_of.get(node, ()))
        queue = next_level
    return tuple(result)


def _map_enumerations(model: CanonicalUmlModel) -> tuple[tuple[EnumType, ...], dict[ElementId, str]]:
    """Stage 2: one `EnumType` per `Enumeration`, **all** enumerations
    emitted regardless of whether any attribute references them
    (DD10) — this keeps the pass single-purpose and order-independent.
    """
    enum_types: list[EnumType] = []
    enum_type_name_by_id: dict[ElementId, str] = {}
    taken_names: set[str] = set()

    for enumeration in model.enumerations:
        name = unique_name(taken_names, snake_case(enumeration.name))
        taken_names.add(name)
        labels = tuple(literal.value or literal.name for literal in enumeration.literals)
        enum_types.append(
            EnumType(name=name, labels=labels, source_enumeration_id=enumeration.id)
        )
        enum_type_name_by_id[enumeration.id] = name

    return tuple(enum_types), enum_type_name_by_id


def _map_attribute_column(
    attribute: UmlAttribute,
    *,
    nullable: bool,
    owner_class_name: str,
    owning_class_id: ElementId,
    enum_type_name_by_id: dict[ElementId, str],
    taken_names: set[str],
    profile: ColumnProfile | None = None,
) -> Column:
    """Attribute -> Column (DD8 naming; type mapping table)."""
    name = unique_name(taken_names, snake_case(attribute.name), owner_class_name)

    if isinstance(attribute.type, EnumerationRef):
        enum_type_name = enum_type_name_by_id.get(attribute.type.enumeration_id)
        if enum_type_name is None:
            raise UnknownEnumerationError(attribute.id, attribute.type.enumeration_id)
        return Column(
            name=name,
            type=ColumnType.ENUM,
            nullable=nullable,
            enum_type_name=enum_type_name,
            source_element_id=attribute.id,
            owning_class_id=owning_class_id,
            profile=profile,
        )

    column_type, extra = _PRIMITIVE_TYPE_MAP[attribute.type]
    return Column(
        name=name,
        type=column_type,
        nullable=nullable,
        source_element_id=attribute.id,
        owning_class_id=owning_class_id,
        profile=profile,
        **extra,
    )


def _map_table_for_root(
    root_id: ElementId,
    *,
    descendants_of: dict[ElementId, tuple[ElementId, ...]],
    class_by_id: dict[ElementId, UmlClass],
    enum_type_name_by_id: dict[ElementId, str],
    taken_table_names: set[str],
    table_profile_by_id: dict[ElementId, TableProfile],
    column_profile_by_id: dict[ElementId, ColumnProfile],
) -> _TableDraft:
    """Stage 3: class(es) -> one `_TableDraft` per generalization root.

    A tree of >= 2 classes collapses to Single Table (DD6): the root's
    table gains every class's columns plus a `class_type` discriminator
    with the verbatim class name per row; a lone class gets no
    discriminator. Root attribute columns are `NOT NULL`; every
    descendant-contributed column is `nullable=True` (DD7).
    """
    tree_class_ids = (root_id,) + descendants_of.get(root_id, ())
    root_class = class_by_id[root_id]

    table_name = unique_name(taken_table_names, snake_case(root_class.name))
    taken_table_names.add(table_name)

    draft = _TableDraft(name=table_name, source_class_ids=tree_class_ids)
    # STI: only the root class's profile becomes the table profile.
    draft.profile = table_profile_by_id.get(root_id)

    id_column = Column(name="id", type=ColumnType.UUID, nullable=False)
    draft.columns.append(id_column)
    draft.column_names.add("id")
    draft.primary_key = PrimaryKey(column_names=("id",), name=f"pk_{table_name}")

    if len(tree_class_ids) >= 2:
        draft.discriminator_column = "class_type"
        draft.column_names.add("class_type")
        draft.columns.append(Column(name="class_type", type=ColumnType.VARCHAR, nullable=False, length=255))
        for class_id in tree_class_ids:
            draft.discriminator_values[class_id] = class_by_id[class_id].name

    for index, class_id in enumerate(tree_class_ids):
        uml_class = class_by_id[class_id]
        nullable = index != 0
        for attribute in uml_class.attributes:
            column = _map_attribute_column(
                attribute,
                nullable=nullable,
                owner_class_name=uml_class.name,
                owning_class_id=class_id,
                enum_type_name_by_id=enum_type_name_by_id,
                taken_names=draft.column_names,
                profile=column_profile_by_id.get(attribute.id),
            )
            draft.columns.append(column)
            draft.column_names.add(column.name)

    return draft


def _is_many(multiplicity: Multiplicity) -> bool:
    """DD11: "many" is `upper is None or upper > 1`."""
    return multiplicity.upper is None or multiplicity.upper > 1


def _root_of(class_id: ElementId, parent_of: dict[ElementId, ElementId]) -> ElementId:
    node = class_id
    while node in parent_of:
        node = parent_of[node]
    return node


def _fk_column_name(
    referenced_end: RelationshipEnd, referenced_table_name: str, taken_names: set[str]
) -> str:
    """DD15 + DD8: role-based when the referenced end has a role, else
    `<referenced_table>_id`, then totalized by `unique_name`.
    """
    preferred = (
        f"{snake_case(referenced_end.role)}_id"
        if referenced_end.role
        else f"{referenced_table_name}_id"
    )
    return unique_name(taken_names, preferred)


def _add_simple_fk(
    *,
    draft: _TableDraft,
    holding_table_name: str,
    referenced_end: RelationshipEnd,
    referenced_table_name: str,
    relationship: Relationship,
    nullable: bool,
    on_delete: ReferentialAction,
    add_unique: bool,
) -> None:
    fk_column_name = _fk_column_name(referenced_end, referenced_table_name, draft.column_names)
    draft.columns.append(Column(name=fk_column_name, type=ColumnType.UUID, nullable=nullable))
    draft.column_names.add(fk_column_name)

    draft.foreign_keys.append(
        ForeignKey(
            name=f"fk_{holding_table_name}__{fk_column_name}",
            column_names=(fk_column_name,),
            referenced_table=referenced_table_name,
            referenced_column_names=("id",),
            on_delete=on_delete,
            source_relationship_id=relationship.id,
        )
    )

    if add_unique:
        draft.unique_constraints.append(
            UniqueConstraint(
                name=f"uq_{holding_table_name}__{fk_column_name}", column_names=(fk_column_name,)
            )
        )
    else:
        # DD17: every FK column gets a non-unique index, except when it
        # already carries a UniqueConstraint (the 1:1 case above).
        draft.indexes.append(
            Index(name=f"ix_{holding_table_name}__{fk_column_name}", column_names=(fk_column_name,))
        )


def _build_join_table(
    relationship: Relationship,
    *,
    source_table_name: str,
    target_table_name: str,
    taken_table_names: set[str],
) -> Table:
    """DD16: join table for a both-ends-many relationship."""
    join_name = unique_name(taken_table_names, f"{source_table_name}_{target_table_name}")
    taken_table_names.add(join_name)

    column_names: set[str] = {"id"}
    pk_column = Column(name="id", type=ColumnType.UUID, nullable=False)

    fk_to_source_name = _fk_column_name(relationship.source, source_table_name, column_names)
    column_names.add(fk_to_source_name)
    fk_to_target_name = _fk_column_name(relationship.target, target_table_name, column_names)
    column_names.add(fk_to_target_name)

    fk_to_source_column = Column(name=fk_to_source_name, type=ColumnType.UUID, nullable=False)
    fk_to_target_column = Column(name=fk_to_target_name, type=ColumnType.UUID, nullable=False)

    fk_to_source = ForeignKey(
        name=f"fk_{join_name}__{fk_to_source_name}",
        column_names=(fk_to_source_name,),
        referenced_table=source_table_name,
        referenced_column_names=("id",),
        on_delete=ReferentialAction.CASCADE,
        source_relationship_id=relationship.id,
    )
    fk_to_target = ForeignKey(
        name=f"fk_{join_name}__{fk_to_target_name}",
        column_names=(fk_to_target_name,),
        referenced_table=target_table_name,
        referenced_column_names=("id",),
        on_delete=ReferentialAction.CASCADE,
        source_relationship_id=relationship.id,
    )

    unique = UniqueConstraint(
        name=f"uq_{join_name}__{fk_to_source_name}_{fk_to_target_name}",
        column_names=(fk_to_source_name, fk_to_target_name),
    )
    index_source = Index(name=f"ix_{join_name}__{fk_to_source_name}", column_names=(fk_to_source_name,))
    index_target = Index(name=f"ix_{join_name}__{fk_to_target_name}", column_names=(fk_to_target_name,))

    return Table(
        name=join_name,
        columns=(pk_column, fk_to_source_column, fk_to_target_column),
        primary_key=PrimaryKey(column_names=("id",), name=f"pk_{join_name}"),
        foreign_keys=(fk_to_source, fk_to_target),
        unique_constraints=(unique,),
        indexes=(index_source, index_target),
    )


def _map_relationships(
    model: CanonicalUmlModel,
    *,
    parent_of: dict[ElementId, ElementId],
    table_name_by_root: dict[ElementId, str],
    drafts: dict[ElementId, _TableDraft],
    taken_table_names: set[str],
) -> tuple[Table, ...]:
    """Stage 4 (design.md "Relationship rule table (DD11-DD17)").

    `GENERALIZATION` relationships contribute nothing (DD19, already
    consumed by Stage 3's Single Table collapse). Every other kind's FK
    or join table is emitted in `model.relationships` order (DD9); an
    endpoint that is a subclass routes to its hierarchy root table
    (DD6).
    """
    join_tables: list[Table] = []

    for relationship in model.relationships:
        if relationship.kind is RelationshipKind.GENERALIZATION:
            continue

        source_class_id = relationship.source.class_id
        target_class_id = relationship.target.class_id
        source_root = _root_of(source_class_id, parent_of)
        target_root = _root_of(target_class_id, parent_of)
        source_table_name = table_name_by_root[source_root]
        target_table_name = table_name_by_root[target_root]
        self_referencing = source_class_id == target_class_id

        source_many = _is_many(relationship.source.multiplicity)
        target_many = _is_many(relationship.target.multiplicity)

        if source_many and target_many:
            join_tables.append(
                _build_join_table(
                    relationship,
                    source_table_name=source_table_name,
                    target_table_name=target_table_name,
                    taken_table_names=taken_table_names,
                )
            )
            continue

        if target_many and not source_many:
            holding_root, holding_table_name = target_root, target_table_name
            referenced_table_name = source_table_name
            referenced_end = relationship.source
            add_unique = False
        elif source_many and not target_many:
            holding_root, holding_table_name = source_root, source_table_name
            referenced_table_name = target_table_name
            referenced_end = relationship.target
            add_unique = False
        else:
            # Neither end many (1:1): FK on the target, referencing the
            # source (DD12) — for COMPOSITION/AGGREGATION, source is the
            # normative whole/owner, so this keeps the part pointing at
            # the whole.
            holding_root, holding_table_name = target_root, target_table_name
            referenced_table_name = source_table_name
            referenced_end = relationship.source
            add_unique = True

        if relationship.kind is RelationshipKind.COMPOSITION:
            # DD13: always NOT NULL + CASCADE, except DD14's documented
            # self-composition exception (a NOT NULL self-FK would make
            # the tree's root row uninsertable).
            nullable = self_referencing
            on_delete = ReferentialAction.CASCADE
        else:  # ASSOCIATION / AGGREGATION
            nullable = referenced_end.multiplicity.lower <= 0  # DD11
            on_delete = ReferentialAction.NO_ACTION

        _add_simple_fk(
            draft=drafts[holding_root],
            holding_table_name=holding_table_name,
            referenced_end=referenced_end,
            referenced_table_name=referenced_table_name,
            relationship=relationship,
            nullable=nullable,
            on_delete=on_delete,
            add_unique=add_unique,
        )

    return tuple(join_tables)


def _freeze_table(draft: _TableDraft) -> Table:
    assert draft.primary_key is not None
    return Table(
        name=draft.name,
        columns=tuple(draft.columns),
        primary_key=draft.primary_key,
        foreign_keys=tuple(draft.foreign_keys),
        unique_constraints=tuple(draft.unique_constraints),
        indexes=tuple(draft.indexes),
        source_class_ids=tuple(draft.source_class_ids),
        discriminator_column=draft.discriminator_column,
        discriminator_values=MappingProxyType(dict(draft.discriminator_values)),
        profile=draft.profile,
    )


def map_to_relational(model: CanonicalUmlModel) -> RelationalModel:
    """The 5-stage pipeline (design.md Data Flow): hierarchy ->
    enumerations -> tables -> relationships -> freeze. Deterministic
    and pure — same `model` always produces a structurally identical
    `RelationalModel` (§21 determinism criterion), since every stage is
    order-preserving per DD9.
    """
    _check_dangling_endpoints(model)
    roots, descendants_of, parent_of = _build_hierarchy(model)
    class_by_id = {uml_class.id: uml_class for uml_class in model.classes}
    attribute_owner_by_id = {
        attribute.id: uml_class.id
        for uml_class in model.classes
        for attribute in uml_class.attributes
    }
    table_profile_by_id, column_profile_by_id = _collect_profiles(
        model, class_by_id, attribute_owner_by_id
    )

    enum_types, enum_type_name_by_id = _map_enumerations(model)

    taken_table_names: set[str] = set()
    drafts: dict[ElementId, _TableDraft] = {}
    table_name_by_root: dict[ElementId, str] = {}
    for root_id in roots:
        draft = _map_table_for_root(
            root_id,
            descendants_of=descendants_of,
            class_by_id=class_by_id,
            enum_type_name_by_id=enum_type_name_by_id,
            taken_table_names=taken_table_names,
            table_profile_by_id=table_profile_by_id,
            column_profile_by_id=column_profile_by_id,
        )
        drafts[root_id] = draft
        table_name_by_root[root_id] = draft.name

    join_tables = _map_relationships(
        model,
        parent_of=parent_of,
        table_name_by_root=table_name_by_root,
        drafts=drafts,
        taken_table_names=taken_table_names,
    )

    root_tables = tuple(_freeze_table(drafts[root_id]) for root_id in roots)
    return RelationalModel(tables=root_tables + join_tables, enum_types=enum_types)
