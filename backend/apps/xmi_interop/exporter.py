"""`ProjectDocument` -> XMI 1.1 / UML 1.3 bytes, in the dialect Enterprise Architect
itself exports (structure mirrored from a real EA 2.5 sample: `XMI.header`,
`UML:Model` > `UML:Package` > `UML:Class`/`UML:Association`, a model-level
`UML:DataType` per primitive, and a `UML:Diagram` carrying the layout).

Choices that were NOT verified against a real EA file (the sample only had
classes, attributes and one plain association): enumerations are written as
`UML:Class` with the `enumeration` stereotype whose attributes are the literals;
generalizations use `subtype`/`supertype`; aggregation/composition use
`aggregation="shared"|"composite"` on the whole end; association connectors in
the diagram use a neutral straight-line geometry. The importer reads all of them back.

Output is deterministic (ids derive from element ids, timestamp from
`updated_at`) and windows-1252 encoded like EA's own files; characters outside
that code page are written as numeric character references.
"""
import re
import uuid
from xml.etree.ElementTree import Element, SubElement, indent, tostring

from apps.relational_mapping.domain.schema import Table
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.uml_modeling.documents import ProjectDocument
from apps.uml_modeling.domain.elements import RelationshipKind, UmlClass
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import EnumerationRef, Multiplicity, PrimitiveType, format_multiplicity

_EA_TYPE_NAMES = {
    PrimitiveType.STRING: "String",
    PrimitiveType.TEXT: "Text",
    PrimitiveType.INTEGER: "int",
    PrimitiveType.LONG: "long",
    PrimitiveType.DECIMAL: "decimal",
    PrimitiveType.BOOLEAN: "boolean",
    PrimitiveType.DATE: "date",
    PrimitiveType.DATETIME: "datetime",
}
_BOX_WIDTH, _BOX_HEIGHT = 117, 71  # size of an EA class box in the sample
# The sample's fixed 71px height (a class with 2-3 attributes) is only tall
# enough for the name compartment plus a couple of rows; a class with more
# attributes/operations than that gets a box too short for EA to render its
# feature compartments, silently hiding them (not verified against a real EA
# row-height constant — generously sized so a too-tall box is the only risk).
_ROW_HEIGHT = 14
_HEADER_HEIGHT = 40  # name compartment + its divider
_GRID_COLUMNS, _GRID_STEP_X, _GRID_STEP_Y = 4, 200, 150
_ILLEGAL_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")


def _clean(text: str) -> str:
    return _ILLEGAL_XML.sub("", text)


def _ea_id(prefix: str, element_id: str) -> str:
    try:
        value = uuid.UUID(hex=element_id)
    except ValueError:
        value = uuid.uuid5(uuid.NAMESPACE_OID, element_id)
    return f"{prefix}_{str(value).upper().replace('-', '_')}"


def _tags(parent: Element, tags: list[tuple[str, str]]) -> None:
    holder = SubElement(parent, "UML:ModelElement.taggedValue")
    for tag, value in tags:
        SubElement(holder, "UML:TaggedValue", {"tag": tag, "value": _clean(value)})


def _is_many(multiplicity: Multiplicity) -> bool:
    """Mirrors `apps.relational_mapping.mapping.mapper._is_many` (DD11)
    WITHOUT importing that app (one-Django-app-per-domain): "many" is
    `upper is None or upper > 1`.
    """
    return multiplicity.upper is None or multiplicity.upper > 1


def _is_join_relationship(relationship) -> bool:
    """Both ends many, mirroring `mapper.py`'s `_map_relationships`
    `source_many and target_many` branch EXACTLY: this applies to ANY
    non-GENERALIZATION relationship kind, not only ASSOCIATION -- `mapper.py`
    never special-cases `kind` before checking both-ends-many.

    A relationship matching this is never part of the UML model itself
    (the join table is computed on the fly by `map_to_relational`), but it
    IS given a visible "association class" here (an empty class linked to
    the SAME single association via the `associationclass`/`conID` tag
    pair -- design.md DD185) so opening the exported XMI in real Enterprise
    Architect shows the join table as its own box, dashed-line-attached to
    the one real `*..*` association, instead of a bare line with nothing
    to hint at the implied join table.
    """
    return _is_many(relationship.source.multiplicity) and _is_many(relationship.target.multiplicity)


def _relational_join_tables(model: CanonicalUmlModel) -> dict[str, Table]:
    """Best-effort {relationship.id: its REAL computed join `Table`}, by
    reusing `map_to_relational` directly (an intentional cross-app read of
    a pure, already-tested function -- the exact reasoning behind
    `apps.relational_mapping.api`'s own `/join-tables` preview endpoint:
    "so the name and columns shown here never drift from what actually
    gets built"). `_is_join_relationship` decides WHICH relationships get
    a join class at all (cheap, always safe); this only ENRICHES that
    join class with the real column names/types when possible.

    Never raises: an invalid model (e.g. a dangling endpoint,
    `map_to_relational` itself would reject) simply gets no enrichment --
    the join class is still written, just empty, exactly as it was
    before this enrichment existed. A join table has no `source_class_ids`
    (that only marks a REAL class's table); each of its foreign keys
    carries `source_relationship_id` back to the relationship it came from.
    """
    try:
        relational = map_to_relational(model)
    except Exception:
        return {}
    tables_by_relationship: dict[str, Table] = {}
    for table in relational.tables:
        if table.source_class_ids:
            continue
        for fk in table.foreign_keys:
            if fk.source_relationship_id is not None:
                tables_by_relationship[fk.source_relationship_id] = table
    return tables_by_relationship


def _unique_join_name(taken: set[str], base: str) -> str:
    """Readable-name counterpart of `mapper.py`'s `unique_name` (that one
    totalizes snake_case SQL table names via `naming.py`; this totalizes a
    human-readable UML class display name), so a colliding join name --
    two both-ends-many relationships between the same pair of classes, or
    a real class already named like the join -- gets a stable numeric
    suffix instead of silently shadowing it. A self-referencing pair
    (`source_name == target_name`) naturally produces e.g. `"C_C"`, which
    cannot collide with the real class `"C"` by construction.
    """
    if base not in taken:
        return base
    suffix = 2
    while f"{base}_{suffix}" in taken:
        suffix += 1
    return f"{base}_{suffix}"


def _plan_join_relationships(model: CanonicalUmlModel, local_ids: dict) -> dict[str, dict]:
    """One plan per both-ends-many relationship: the synthetic association
    class's name/xmi.id/ea_localid. Extends `local_ids` IN PLACE with one
    entry per join class (own `ea_localid`, used the same way a real
    class's would be for `ea_sourceID`/`ea_targetID`-style tags and for
    diagram positioning). Ids are derived deterministically from the
    ORIGINAL relationship's id via `_ea_id`, suffixed so they can never
    collide with a real class/relationship id (a different name string
    hashes to a different UUID5) and stay stable across repeated exports
    of the unchanged document.
    """
    taken_names = {c.name for c in model.classes} | {e.name for e in model.enumerations}
    relational_tables = _relational_join_tables(model)
    plans: dict[str, dict] = {}
    next_local = max(local_ids.values(), default=0) + 1
    for relationship in model.relationships:
        if relationship.kind is RelationshipKind.GENERALIZATION:
            continue
        if not _is_join_relationship(relationship):
            continue
        source_name = model.class_by_id(relationship.source.class_id).name
        target_name = model.class_by_id(relationship.target.class_id).name
        join_name = _unique_join_name(taken_names, f"{source_name}_{target_name}")
        taken_names.add(join_name)
        key = f"{relationship.id}:join"
        local_ids[key] = next_local
        next_local += 1
        plans[relationship.id] = {
            "key": key,
            "ea_id": _ea_id("EAID", key),
            "name": join_name,
            "source_class_id": relationship.source.class_id,
            "target_class_id": relationship.target.class_id,
            "table": relational_tables.get(relationship.id),
        }
    return plans


def export_xmi(document: ProjectDocument) -> bytes:
    model = document.model
    name = _clean(document.metadata.name)
    stamp = document.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    package_id = _ea_id("EAPK", str(document.id))
    class_ids = {c.id: _ea_id("EAID", c.id) for c in model.classes}
    enum_ids = {e.id: _ea_id("EAID", e.id) for e in model.enumerations}
    local_ids = {element_id: index for index, element_id in enumerate({**class_ids, **enum_ids}, start=1)}
    join_info = _plan_join_relationships(model, local_ids)

    root = Element("XMI", {"xmi.version": "1.1", "xmlns:UML": "omg.org/UML1.3", "timestamp": stamp})
    documentation = SubElement(SubElement(root, "XMI.header"), "XMI.documentation")
    SubElement(documentation, "XMI.exporter").text = "Enterprise Architect"
    SubElement(documentation, "XMI.exporterVersion").text = "2.5"
    content = SubElement(root, "XMI.content")
    uml_model = SubElement(
        content, "UML:Model", {"name": "EA Model", "xmi.id": _ea_id("MX_EAID", str(document.id))}
    )
    owned = SubElement(uml_model, "UML:Namespace.ownedElement")
    SubElement(
        owned,
        "UML:Class",
        {"name": "EARootClass", "xmi.id": "EAID_11111111_5487_4080_A7F4_41526CB0AA00", "isRoot": "true",
         "isLeaf": "false", "isAbstract": "false"},
    )
    package = SubElement(
        owned,
        "UML:Package",
        {"name": name, "xmi.id": package_id, "isRoot": "false", "isLeaf": "false", "isAbstract": "false",
         "visibility": "public"},
    )
    package_owned = SubElement(package, "UML:Namespace.ownedElement")

    datatype_ids: dict[PrimitiveType, str] = {}

    def datatype_id(primitive: PrimitiveType) -> str:
        return datatype_ids.setdefault(primitive, f"eaxmiid{len(datatype_ids)}")

    for uml_class in model.classes:
        _write_class(package_owned, uml_class, model, package_id, name, class_ids, local_ids, datatype_id, enum_ids)
    for enumeration in model.enumerations:
        _write_enumeration(package_owned, enumeration, package_id, name, enum_ids, local_ids)
    for relationship in model.relationships:
        plan = join_info.get(relationship.id)
        if plan is not None:
            _write_join_class(package_owned, plan, package_id, name, local_ids[plan["key"]], _ea_id("EAID", relationship.id))
        _write_relationship(
            package_owned, relationship, model, class_ids, local_ids,
            join_class_ea_id=plan["ea_id"] if plan is not None else None,
        )
    for primitive, xid in datatype_ids.items():
        SubElement(
            owned,
            "UML:DataType",
            {"xmi.id": xid, "name": _EA_TYPE_NAMES[primitive], "visibility": "private", "isRoot": "false",
             "isLeaf": "false", "isAbstract": "false"},
        )

    _write_diagram(content, document, package_id, name, class_ids, enum_ids, join_info)
    SubElement(root, "XMI.difference")
    SubElement(SubElement(root, "XMI.extensions", {"xmi.extender": "Enterprise Architect 2.5"}), "EAModel.paramSub")

    indent(root, space="\t")
    return tostring(root, encoding="windows-1252", xml_declaration=True)


def _class_tags(package_id: str, package_name: str, local_id: int, stereotype: str) -> list[tuple[str, str]]:
    return [
        ("isSpecification", "false"),
        ("ea_stype", stereotype),
        ("ea_ntype", "0"),
        ("version", "1.0"),
        ("package", package_id),
        ("package_name", package_name),
        ("ea_localid", str(local_id)),
        ("ea_eleType", "element"),
    ]


def _write_class(
    parent: Element,
    uml_class: UmlClass,
    model: CanonicalUmlModel,
    package_id: str,
    package_name: str,
    class_ids: dict,
    local_ids: dict,
    datatype_id,
    enum_ids: dict,
) -> None:
    element = SubElement(
        parent,
        "UML:Class",
        {"name": _clean(uml_class.name), "xmi.id": class_ids[uml_class.id], "visibility": uml_class.visibility.value,
         "namespace": package_id, "isRoot": "false", "isLeaf": "false", "isAbstract": "false", "isActive": "false"},
    )
    _tags(element, _class_tags(package_id, package_name, local_ids[uml_class.id], "Class"))
    features = SubElement(element, "UML:Classifier.feature")
    for position, attribute in enumerate(uml_class.attributes):
        if isinstance(attribute.type, EnumerationRef):
            type_name = model.enumeration_by_id(attribute.type.enumeration_id).name
            type_ref = enum_ids[attribute.type.enumeration_id]
        else:
            type_name = _EA_TYPE_NAMES[attribute.type]
            type_ref = datatype_id(attribute.type)
        node = SubElement(
            features,
            "UML:Attribute",
            {"name": _clean(attribute.name), "changeable": "none", "visibility": attribute.visibility.value,
             "ownerScope": "instance", "targetScope": "instance"},
        )
        SubElement(SubElement(node, "UML:Attribute.initialValue"), "UML:Expression")
        SubElement(SubElement(node, "UML:StructuralFeature.type"), "UML:Classifier", {"xmi.idref": type_ref})
        _tags(node, [("type", _clean(type_name)), ("position", str(position)), ("lowerBound", "1"), ("upperBound", "1")])
    for operation in uml_class.operations:
        SubElement(
            features,
            "UML:Operation",
            {"name": _clean(operation.name), "visibility": operation.visibility.value, "ownerScope": "instance"},
        )


def _write_enumeration(parent, enumeration, package_id, package_name, enum_ids, local_ids) -> None:
    element = SubElement(
        parent,
        "UML:Class",
        {"name": _clean(enumeration.name), "xmi.id": enum_ids[enumeration.id], "visibility": "public",
         "namespace": package_id, "isRoot": "false", "isLeaf": "false", "isAbstract": "false", "isActive": "false"},
    )
    _tags(element, _class_tags(package_id, package_name, local_ids[enumeration.id], "Enumeration"))
    SubElement(SubElement(element, "UML:ModelElement.stereotype"), "UML:Stereotype", {"name": "enumeration"})
    features = SubElement(element, "UML:Classifier.feature")
    for literal in enumeration.literals:
        SubElement(features, "UML:Attribute", {"name": _clean(literal.name), "visibility": "public"})


_WHOLE_END_AGGREGATION = {RelationshipKind.AGGREGATION: "shared", RelationshipKind.COMPOSITION: "composite"}


def _write_relationship(parent, relationship, model, class_ids, local_ids, *, join_class_ea_id: str | None = None) -> None:
    """`join_class_ea_id`: for a both-ends-many relationship, the plain
    association below gets two extra tagged values -- `associationclass`
    (pointing at the join class's `xmi.id`) and `subtype="Class"` -- the
    EXACT marker real Enterprise Architect writes for a genuine UML
    "Association Class" (verified from a real EA export the user made
    themselves: attaching a class to this association in EA produces
    precisely these two tags, nothing else different about the
    association itself; design.md DD185). No separate synthetic
    associations are written -- the real `*..*` association is the only
    one, exactly as for any other relationship.
    """
    source, target = relationship.source, relationship.target
    source_name = model.class_by_id(source.class_id).name
    target_name = model.class_by_id(target.class_id).name
    rel_id = _ea_id("EAID", relationship.id)
    endpoint_tags = [
        ("ea_sourceName", source_name), ("ea_targetName", target_name),
        ("ea_sourceType", "Class"), ("ea_targetType", "Class"),
        ("ea_sourceID", str(local_ids[source.class_id])), ("ea_targetID", str(local_ids[target.class_id])),
    ]
    if relationship.kind is RelationshipKind.GENERALIZATION:
        element = SubElement(
            parent,
            "UML:Generalization",
            {"xmi.id": rel_id, "subtype": class_ids[source.class_id], "supertype": class_ids[target.class_id],
             "visibility": "public", "isSpecification": "false"},
        )
        _tags(element, [("ea_type", "Generalization"), ("direction", "Source -> Destination"), *endpoint_tags])
        return

    element = SubElement(
        parent,
        "UML:Association",
        {"name": _clean(relationship.name or ""), "xmi.id": rel_id, "visibility": "public", "isRoot": "false",
         "isLeaf": "false", "isAbstract": "false"},
    )
    ea_type = "Association" if relationship.kind is RelationshipKind.ASSOCIATION else "Aggregation"
    association_class_tags = (
        [("subtype", "Class"), ("associationclass", join_class_ea_id)] if join_class_ea_id is not None else []
    )
    _tags(
        element,
        [("ea_type", ea_type), ("direction", "Unspecified"), *endpoint_tags, *association_class_tags,
         ("lb", format_multiplicity(source.multiplicity)), ("mt", _clean(relationship.name or "")),
         ("rb", format_multiplicity(target.multiplicity))],
    )
    connection = SubElement(element, "UML:Association.connection")
    for end, ea_end in ((source, "source"), (target, "target")):
        attributes = {
            "visibility": "public",
            "multiplicity": format_multiplicity(end.multiplicity),
            "aggregation": _WHOLE_END_AGGREGATION.get(relationship.kind, "none") if end is source else "none",
            "isOrdered": "false", "targetScope": "instance", "changeable": "none", "isNavigable": "true",
            "type": class_ids[end.class_id],
        }
        if end.role:
            attributes["name"] = _clean(end.role)
        node = SubElement(connection, "UML:AssociationEnd", attributes)
        _tags(node, [("containment", "Unspecified"), ("ea_end", ea_end)])


_MODELIA_SYNTHETIC_TAG = ("modelia_synthetic", "join_table")


def _write_join_class(
    parent, plan: dict, package_id: str, package_name: str, local_id: int, association_ea_id: str
) -> None:
    """A `UML:Class` representing a both-ends-many relationship's
    materialized join table (see `_plan_join_relationships`). Never part
    of `model.classes` -- this is display-only, mirroring how
    `apps.relational_mapping.mapping.mapper._build_join_table` computes
    the join table on the fly rather than storing it in the UML model.
    When `plan["table"]` is available (the model mapped cleanly via
    `_relational_join_tables`), its REAL columns are written as this
    class's attributes -- purely informational, matching exactly what
    Modelia's own join-table preview hint already shows on the canvas.
    When it isn't (an invalid model `map_to_relational` couldn't map),
    the class is left empty, as before this enrichment existed.

    `conID` is the REAL Enterprise Architect tag (verified from a real EA
    export) an association class carries back to its owning association --
    the reverse of the association's own `associationclass` tag
    (`_write_relationship`). Both point at each other; EA uses this pair
    to draw the dashed line from the class to the association.

    `modelia_synthetic` is OUR OWN marker (EA safely ignores unknown
    tags, standard XMI extensibility), not a real EA convention -- since
    this class may now carry real-looking attributes, the importer can no
    longer tell "ours" from "a real association class the user built in
    EA" just by checking for zero attributes
    (`importer._hide_association_classes`'s original signal). This tag is
    the reliable one now; emptiness stays a fallback for a genuine
    EA-authored association class that never carried this tag.
    """
    element = SubElement(
        parent,
        "UML:Class",
        {"name": _clean(plan["name"]), "xmi.id": plan["ea_id"], "visibility": "public", "namespace": package_id,
         "isRoot": "false", "isLeaf": "false", "isAbstract": "false", "isActive": "false"},
    )
    _tags(
        element,
        [*_class_tags(package_id, package_name, local_id, "Class"), ("conID", association_ea_id), _MODELIA_SYNTHETIC_TAG],
    )
    features = SubElement(element, "UML:Classifier.feature")
    table = plan.get("table")
    if table is not None:
        for column in table.columns:
            node = SubElement(
                features,
                "UML:Attribute",
                {"name": _clean(column.name), "visibility": "public", "ownerScope": "instance", "targetScope": "instance"},
            )
            _tags(node, [("type", column.type.value)])


def _box_height(feature_rows: int) -> int:
    """Enough room for the name compartment plus one row per attribute/operation
    (never below the sample's floor, so a featureless class keeps its old size)."""
    return max(_BOX_HEIGHT, _HEADER_HEIGHT + feature_rows * _ROW_HEIGHT)


def _write_diagram(content, document, package_id, package_name, class_ids, enum_ids, join_info: dict) -> None:
    diagram = SubElement(
        content,
        "UML:Diagram",
        {"name": package_name, "xmi.id": _ea_id("EAID", f"diagram-{document.id}"), "diagramType": "ClassDiagram",
         "owner": package_id, "toolName": "Enterprise Architect 2.5"},
    )
    _tags(diagram, [("version", "1.0"), ("package", package_id), ("type", "Logical"), ("ea_localid", "1")])
    elements = SubElement(diagram, "UML:Diagram.element")
    seqno = 0
    node_ids = {**class_ids, **enum_ids}
    feature_rows: dict[str, int] = {
        **{c.id: len(c.attributes) + len(c.operations) for c in document.model.classes},
        **{e.id: len(e.literals) for e in document.model.enumerations},
    }

    # Pass 1: real classes/enumerations, exactly as before (explicit
    # layout position, else a deterministic grid fallback).
    positions: dict[str, tuple[float, float, int]] = {}
    for index, element_id in enumerate(node_ids):
        position = document.layout.positions.get(element_id)
        height = _box_height(feature_rows.get(element_id, 0))
        x = position.x if position else 100 + _BOX_WIDTH / 2 + (index % _GRID_COLUMNS) * _GRID_STEP_X
        y = position.y if position else 100 + height / 2 + (index // _GRID_COLUMNS) * _GRID_STEP_Y
        positions[element_id] = (x, y, height)

    # Pass 2: synthetic join classes are never in the layout -- position
    # each at the midpoint of its two related classes (already resolved
    # above), offset a bit so a self-referencing join (whose "midpoint" is
    # the single related class's own position) doesn't render on top of it.
    join_node_ids: dict[str, str] = {}
    for plan in join_info.values():
        source_x, source_y, _source_h = positions[plan["source_class_id"]]
        target_x, target_y, _target_h = positions[plan["target_class_id"]]
        positions[plan["key"]] = (
            (source_x + target_x) / 2 + 40,
            (source_y + target_y) / 2 + 40,
            _box_height(0),
        )
        join_node_ids[plan["key"]] = plan["ea_id"]
    node_ids = {**node_ids, **join_node_ids}

    for element_id, xid in node_ids.items():
        seqno += 1
        x, y, height = positions[element_id]
        left, top = round(x - _BOX_WIDTH / 2), round(y - height / 2)
        SubElement(
            elements,
            "UML:DiagramElement",
            {"geometry": f"Left={left};Top={top};Right={left + _BOX_WIDTH};Bottom={top + height};",
             "subject": xid, "seqno": str(seqno), "style": "ImageID=0;"},
        )
    for relationship in document.model.relationships:
        # A both-ends-many relationship keeps its own single real
        # association (see `_write_relationship`'s `join_class_ea_id`
        # param) -- there is only ever one edge to draw per relationship,
        # same as any other. EA draws the association-class's dashed
        # connector itself from the `associationclass`/`conID` tag pair,
        # not from anything in the diagram geometry.
        seqno += 1
        SubElement(
            elements,
            "UML:DiagramElement",
            {"geometry": "SX=0;SY=0;EX=0;EY=0;EDGE=1;Path=;", "subject": _ea_id("EAID", relationship.id),
             "seqno": str(seqno), "style": "Mode=3;Color=-1;LWidth=0;Hidden=0;"},
        )
