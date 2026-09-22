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

from apps.uml_modeling.documents import ProjectDocument
from apps.uml_modeling.domain.elements import RelationshipKind, UmlClass
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import EnumerationRef, PrimitiveType, format_multiplicity

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


def export_xmi(document: ProjectDocument) -> bytes:
    model = document.model
    name = _clean(document.metadata.name)
    stamp = document.updated_at.strftime("%Y-%m-%d %H:%M:%S")
    package_id = _ea_id("EAPK", str(document.id))
    class_ids = {c.id: _ea_id("EAID", c.id) for c in model.classes}
    enum_ids = {e.id: _ea_id("EAID", e.id) for e in model.enumerations}
    local_ids = {element_id: index for index, element_id in enumerate({**class_ids, **enum_ids}, start=1)}

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
        _write_relationship(package_owned, relationship, model, class_ids, local_ids)
    for primitive, xid in datatype_ids.items():
        SubElement(
            owned,
            "UML:DataType",
            {"xmi.id": xid, "name": _EA_TYPE_NAMES[primitive], "visibility": "private", "isRoot": "false",
             "isLeaf": "false", "isAbstract": "false"},
        )

    _write_diagram(content, document, package_id, name, class_ids, enum_ids)
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


def _write_relationship(parent, relationship, model, class_ids, local_ids) -> None:
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
    _tags(
        element,
        [("ea_type", ea_type), ("direction", "Unspecified"), *endpoint_tags,
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


def _box_height(feature_rows: int) -> int:
    """Enough room for the name compartment plus one row per attribute/operation
    (never below the sample's floor, so a featureless class keeps its old size)."""
    return max(_BOX_HEIGHT, _HEADER_HEIGHT + feature_rows * _ROW_HEIGHT)


def _write_diagram(content, document, package_id, package_name, class_ids, enum_ids) -> None:
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
    for index, (element_id, xid) in enumerate(node_ids.items()):
        seqno += 1
        position = document.layout.positions.get(element_id)
        height = _box_height(feature_rows.get(element_id, 0))
        x = position.x if position else 100 + _BOX_WIDTH / 2 + (index % _GRID_COLUMNS) * _GRID_STEP_X
        y = position.y if position else 100 + height / 2 + (index // _GRID_COLUMNS) * _GRID_STEP_Y
        left, top = round(x - _BOX_WIDTH / 2), round(y - height / 2)
        SubElement(
            elements,
            "UML:DiagramElement",
            {"geometry": f"Left={left};Top={top};Right={left + _BOX_WIDTH};Bottom={top + height};",
             "subject": xid, "seqno": str(seqno), "style": "ImageID=0;"},
        )
    for relationship in document.model.relationships:
        seqno += 1
        SubElement(
            elements,
            "UML:DiagramElement",
            {"geometry": "SX=0;SY=0;EX=0;EY=0;EDGE=1;Path=;", "subject": _ea_id("EAID", relationship.id),
             "seqno": str(seqno), "style": "Mode=3;Color=-1;LWidth=0;Hidden=0;"},
        )
