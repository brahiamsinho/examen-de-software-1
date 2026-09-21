"""Enterprise Architect XMI -> `CanonicalUmlModel` (parser -> validator -> model).

Two readers (XMI 1.1 / UML 1.3 as EA exports it, verified against a real EA
sample; and a basic XMI 2.1 reader, verified ONLY against a hand-written
fixture) fill one neutral `_Raw` structure. `_build` then maps it to the
canonical model, so mapping rules live in exactly one place.

Policies (each one is reported as a warning, never as a failure):
- Unsupported elements (Actor, UseCase, Dependency, Interface, ...) are skipped.
  EA plumbing (EARootClass, DataType, Diagram, Stereotype) is skipped silently.
- Unknown attribute types fall back to `String`. An attribute typed by a class
  is skipped (the canonical model expresses class links only as relationships).
- Attribute multiplicity, operation parameters/return types are not imported.
- A missing association-end multiplicity is assumed `0..*`.
- Associations with a missing/unsupported endpoint or != 2 ends are skipped.
- Validation diagnostics of the canonical rules are appended as warnings; the
  import itself never fails because of them (the editor shows them too).

Direction convention: for aggregation/composition the WHOLE (diamond) end is the
canonical `source`. In UML 1.x the whole is the end carrying `aggregation`; in
UML 2 the property carrying `aggregation="composite"` is the PART, so the 2.x
reader moves the hint to the opposite end.

Parsing is done on BYTES (EA declares windows-1252) with `defusedxml`, which
rejects DTD entities (XXE, billion laughs).
"""
import re
from dataclasses import dataclass, field
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from apps.uml_modeling.documents import DiagramLayout, Position
from apps.uml_modeling.domain.elements import (
    Enumeration,
    EnumerationLiteral,
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
    UmlOperation,
    Visibility,
)
from apps.uml_modeling.domain.ids import ElementId, new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import (
    AttributeType,
    EnumerationRef,
    Multiplicity,
    PrimitiveType,
    parse_multiplicity,
)
from apps.uml_modeling.validation.engine import validate
from apps.xmi_interop.errors import InvalidXmiError, UnsupportedXmiError

MAX_XMI_BYTES = 5 * 1024 * 1024

_PRIMITIVES: dict[str, PrimitiveType] = {
    **dict.fromkeys(("int", "integer", "short", "byte", "smallint", "int32", "uint"), PrimitiveType.INTEGER),
    **dict.fromkeys(("long", "bigint", "int64"), PrimitiveType.LONG),
    **dict.fromkeys(("string", "varchar", "char", "character", "nvarchar"), PrimitiveType.STRING),
    **dict.fromkeys(("text", "clob"), PrimitiveType.TEXT),
    **dict.fromkeys(("double", "float", "decimal", "numeric", "real", "number", "money"), PrimitiveType.DECIMAL),
    **dict.fromkeys(("bool", "boolean", "bit"), PrimitiveType.BOOLEAN),
    "date": PrimitiveType.DATE,
    **dict.fromkeys(("datetime", "timestamp", "time"), PrimitiveType.DATETIME),
}
_SILENT_ELEMENTS = frozenset({"DataType", "PrimitiveType", "Diagram", "Stereotype", "TagDefinition", "TaggedValue"})
_VISIBILITIES = {v.value: v for v in Visibility}
_DEFAULT_MULTIPLICITY = "0..*"


# --- neutral intermediate structure ----------------------------------------


@dataclass
class _RawAttribute:
    name: str
    type_name: str | None = None
    type_ref: str | None = None
    visibility: str | None = None
    upper: str | None = None


@dataclass
class _RawClass:
    xid: str
    name: str
    attributes: list[_RawAttribute] = field(default_factory=list)
    operations: list[tuple[str, str | None, bool]] = field(default_factory=list)  # name, visibility, has_signature
    literals: list[str] | None = None  # not None => an enumeration
    visibility: str | None = None


@dataclass
class _RawEnd:
    class_ref: str | None
    multiplicity: str | None
    whole: bool  # this end carries the diamond (already normalized to UML 1.x semantics)
    kind: RelationshipKind = RelationshipKind.ASSOCIATION
    role: str | None = None


@dataclass
class _RawAssociation:
    name: str | None
    ends: list[_RawEnd]


@dataclass
class _Raw:
    classes: list[_RawClass] = field(default_factory=list)
    associations: list[_RawAssociation] = field(default_factory=list)
    generalizations: list[tuple[str | None, str | None]] = field(default_factory=list)  # child, parent
    datatypes: dict[str, str] = field(default_factory=dict)
    positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    diagram_name: str | None = None
    package_name: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ImportResult:
    model: CanonicalUmlModel
    layout: DiagramLayout
    warnings: tuple[str, ...]
    name: str | None


# --- XML helpers (namespace-agnostic) ----------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _kids(el: Element, name: str) -> list[Element]:
    return [c for c in el if _local(c.tag) == name]


def _kid(el: Element, name: str) -> Element | None:
    return next(iter(_kids(el, name)), None)


def _xmi(el: Element, name: str) -> str | None:
    """A namespaced XMI attribute (`xmi:id`, `xmi:type`, `xmi:idref`) by local name."""
    for key, value in el.attrib.items():
        if key.startswith("{") and key.endswith("}" + name):
            return value
    return None


def _tagged(el: Element) -> dict[str, str]:
    holder = _kid(el, "ModelElement.taggedValue")
    if holder is None:
        return {}
    return {t.get("tag", ""): t.get("value", "") for t in _kids(holder, "TaggedValue")}


def _idref_below(el: Element) -> str | None:
    for node in el.iter():
        ref = node.get("xmi.idref") or _xmi(node, "idref")
        if ref:
            return ref
    return None


def _visibility(value: str | None) -> Visibility | None:
    return _VISIBILITIES.get((value or "").lower())


# --- XMI 1.1 / UML 1.3 reader ---------------------------------------------------


def _read_v1(root: Element, raw: _Raw) -> None:
    content = _kid(root, "XMI.content")
    model = next((n for n in content.iter() if _local(n.tag) == "Model"), None) if content is not None else None
    if model is None:
        raise UnsupportedXmiError("El XMI no contiene un UML:Model.")
    _walk_v1(model, raw)
    _read_v1_diagrams(content, raw)


def _walk_v1(container: Element, raw: _Raw) -> None:
    owned = _kid(container, "Namespace.ownedElement")
    for el in owned if owned is not None else ():
        kind = _local(el.tag)
        name = el.get("name", "")
        if kind == "Package":
            raw.package_name = raw.package_name or name
            _walk_v1(el, raw)
        elif kind == "Class":
            _read_class_v1(el, raw)
        elif kind == "Enumeration":
            literals = [lit.get("name", "") for lit in el.iter() if _local(lit.tag) == "EnumerationLiteral"]
            raw.classes.append(_RawClass(el.get("xmi.id", ""), name, literals=literals))
        elif kind == "Association":
            _read_association_v1(el, raw)
        elif kind == "Generalization":
            child = el.get("child") or el.get("subtype") or _idref_below_kid(el, "Generalization.child")
            parent = el.get("parent") or el.get("supertype") or _idref_below_kid(el, "Generalization.parent")
            raw.generalizations.append((child, parent))
        elif kind == "DataType":
            raw.datatypes[el.get("xmi.id", "")] = name
        elif kind not in _SILENT_ELEMENTS:
            raw.warnings.append(f"Se ignoró el elemento no soportado '{kind}' ({name or 'sin nombre'}).")


def _idref_below_kid(el: Element, name: str) -> str | None:
    holder = _kid(el, name)
    return _idref_below(holder) if holder is not None else None


def _read_class_v1(el: Element, raw: _Raw) -> None:
    tags = _tagged(el)
    name = el.get("name", "")
    if el.get("isRoot") == "true" or name == "EARootClass" or tags.get("ea_stype") == "EAStub":
        return
    stereotype = next((s.get("name", "") for s in el.iter() if _local(s.tag) == "Stereotype"), "")
    is_enum = tags.get("ea_stype") == "Enumeration" or stereotype.lower() == "enumeration"
    raw_class = _RawClass(el.get("xmi.id", ""), name, visibility=el.get("visibility"))
    features = _kid(el, "Classifier.feature")
    for feature in features if features is not None else ():
        kind = _local(feature.tag)
        if kind == "Attribute":
            if is_enum:
                raw_class.literals = (raw_class.literals or []) + [feature.get("name", "")]
                continue
            ftags = _tagged(feature)
            type_holder = _kid(feature, "StructuralFeature.type")
            raw_class.attributes.append(
                _RawAttribute(
                    name=feature.get("name", ""),
                    type_name=ftags.get("type") or None,
                    type_ref=_idref_below(type_holder) if type_holder is not None else None,
                    visibility=feature.get("visibility"),
                    upper=ftags.get("upperBound"),
                )
            )
        elif kind == "Operation":
            has_signature = any(_local(n.tag) == "Parameter" for n in feature.iter())
            raw_class.operations.append((feature.get("name", ""), feature.get("visibility"), has_signature))
    if is_enum and raw_class.literals is None:
        raw_class.literals = []
    raw.classes.append(raw_class)


def _read_association_v1(el: Element, raw: _Raw) -> None:
    connection = _kid(el, "Association.connection")
    ends: list[_RawEnd] = []
    for end in _kids(connection, "AssociationEnd") if connection is not None else ():
        aggregation = (end.get("aggregation") or "none").lower()
        ends.append(
            _RawEnd(
                class_ref=end.get("type") or _idref_below(end),
                multiplicity=end.get("multiplicity") or None,
                whole=aggregation in {"aggregate", "shared", "composite"},
                kind=RelationshipKind.COMPOSITION if aggregation == "composite" else RelationshipKind.AGGREGATION,
                role=end.get("name") or None,
            )
        )
    raw.associations.append(_RawAssociation(el.get("name") or None, ends))


_GEOMETRY = re.compile(r"(Left|Top|Right|Bottom)=(-?\d+(?:\.\d+)?)")


def _read_v1_diagrams(content: Element, raw: _Raw) -> None:
    diagrams = [d for d in content.iter() if _local(d.tag) == "Diagram"]
    diagrams.sort(key=lambda d: d.get("diagramType") != "ClassDiagram")  # class diagrams first (stable)
    for diagram in diagrams:
        if raw.diagram_name is None and diagram.get("diagramType") in (None, "ClassDiagram"):
            raw.diagram_name = diagram.get("name") or None
        for element in (e for e in diagram.iter() if _local(e.tag) == "DiagramElement"):
            geometry = dict(_GEOMETRY.findall(element.get("geometry", "")))
            subject = element.get("subject")
            if subject and "Left" in geometry and "Top" in geometry:
                left, top = float(geometry["Left"]), float(geometry["Top"])
                right, bottom = float(geometry.get("Right", left)), float(geometry.get("Bottom", top))
                raw.positions.setdefault(subject, ((left + right) / 2, (top + bottom) / 2))


# --- XMI 2.x reader ----------------------------------------------------------------


def _read_v2(root: Element, raw: _Raw) -> None:
    model = root if _local(root.tag) == "Model" else next((n for n in root.iter() if _local(n.tag) == "Model"), None)
    if model is None:
        raise UnsupportedXmiError("El XMI no contiene un uml:Model.")
    ends_by_id: dict[str, Element] = {}
    associations: list[Element] = []
    _walk_v2(model, raw, ends_by_id, associations)
    for association in associations:
        for owned_end in _kids(association, "ownedEnd"):
            ends_by_id[_xmi(owned_end, "id") or ""] = owned_end
        member_ids = (association.get("memberEnd") or "").split() or [
            _xmi(m, "idref") or "" for m in _kids(association, "memberEnd")
        ]
        raw.associations.append(
            _RawAssociation(association.get("name") or None, _normalize_ends_v2([ends_by_id.get(i) for i in member_ids]))
        )


def _walk_v2(container: Element, raw: _Raw, ends_by_id: dict[str, Element], associations: list[Element]) -> None:
    for el in _kids(container, "packagedElement"):
        kind = (_xmi(el, "type") or "").split(":")[-1]
        name, xid = el.get("name", ""), _xmi(el, "id") or ""
        if kind == "Package":
            raw.package_name = raw.package_name or name
            _walk_v2(el, raw, ends_by_id, associations)
        elif kind == "Class":
            _read_class_v2(el, raw, ends_by_id)
        elif kind == "Enumeration":
            literals = [lit.get("name", "") for lit in _kids(el, "ownedLiteral")]
            raw.classes.append(_RawClass(xid, name, literals=literals))
        elif kind == "Association":
            associations.append(el)
        elif kind in ("PrimitiveType", "DataType"):
            raw.datatypes[xid] = name
        else:
            raw.warnings.append(f"Se ignoró el elemento no soportado '{kind or 'desconocido'}' ({name or 'sin nombre'}).")


def _type_of_v2(prop: Element) -> str | None:
    """Type reference of a `Property`: `type="id"`, `<type xmi:idref>` or a `href="...#Name"`."""
    if prop.get("type"):
        return prop.get("type")
    type_el = _kid(prop, "type")
    if type_el is None:
        return None
    return _xmi(type_el, "idref") or (type_el.get("href") or "").rsplit("#", 1)[-1] or None


def _read_class_v2(el: Element, raw: _Raw, ends_by_id: dict[str, Element]) -> None:
    xid = _xmi(el, "id") or ""
    raw_class = _RawClass(xid, el.get("name", ""), visibility=el.get("visibility"))
    for prop in _kids(el, "ownedAttribute"):
        if prop.get("association"):  # an association end owned by the class, not a real attribute
            ends_by_id[_xmi(prop, "id") or ""] = prop
            continue
        upper = _kid(prop, "upperValue")
        type_ref = _type_of_v2(prop)
        raw_class.attributes.append(
            _RawAttribute(
                name=prop.get("name", ""),
                type_ref=type_ref,
                type_name=re.sub(r"^EA[A-Za-z]+_", "", type_ref) if type_ref else None,
                visibility=prop.get("visibility"),
                upper=upper.get("value") if upper is not None else None,
            )
        )
    for operation in _kids(el, "ownedOperation"):
        signature = bool(_kids(operation, "ownedParameter"))
        raw_class.operations.append((operation.get("name", ""), operation.get("visibility"), signature))
    for generalization in _kids(el, "generalization"):
        raw.generalizations.append((xid, generalization.get("general") or _idref_below(generalization)))
    raw.classes.append(raw_class)


def _multiplicity_v2(prop: Element) -> str:
    lower, upper = _kid(prop, "lowerValue"), _kid(prop, "upperValue")
    low = lower.get("value", "0") if lower is not None else "1"
    up = upper.get("value", "*") if upper is not None else "1"
    return low if low == up else f"{low}..{up}"


def _normalize_ends_v2(props: list[Element | None]) -> list[_RawEnd]:
    ends: list[_RawEnd] = []
    part_kinds: list[RelationshipKind | None] = []
    for prop in props:
        if prop is None:
            ends.append(_RawEnd(None, None, False))
            part_kinds.append(None)
            continue
        aggregation = (prop.get("aggregation") or "none").lower()
        part_kinds.append(
            RelationshipKind.COMPOSITION
            if aggregation == "composite"
            else RelationshipKind.AGGREGATION
            if aggregation == "shared"
            else None
        )
        ends.append(_RawEnd(_type_of_v2(prop), _multiplicity_v2(prop), False, role=prop.get("name") or None))
    # UML 2: the property tagged composite/shared is the PART; the diamond is on the other end.
    if len(ends) == 2:
        for index, part_kind in enumerate(part_kinds):
            if part_kind is not None:
                ends[1 - index].whole = True
                ends[1 - index].kind = part_kind
    return ends


# --- canonical mapping --------------------------------------------------------------


def _resolve_type(
    attribute: _RawAttribute,
    owner: str,
    raw: _Raw,
    enum_ids: dict[str, ElementId],
    enum_names: dict[str, ElementId],
    class_refs: set[str],
    warnings: list[str],
) -> AttributeType | None:
    where = f"{owner}.{attribute.name}"
    ref, name = attribute.type_ref, attribute.type_name
    if ref in enum_ids:
        return EnumerationRef(enum_ids[ref])
    if ref in class_refs or (name is not None and name in class_refs):
        warnings.append(
            f"Se ignoró el atributo '{where}': su tipo es una clase (modélelo como una relación)."
        )
        return None
    if ref in raw.datatypes:
        name = raw.datatypes[ref]
    if name in enum_names:
        return EnumerationRef(enum_names[name])
    primitive = _PRIMITIVES.get((name or "").strip().lower())
    if primitive is None:
        warnings.append(f"Tipo desconocido '{name or 'sin tipo'}' en '{where}': se usó String.")
        return PrimitiveType.STRING
    return primitive


def _multiplicity(text: str | None, where: str, warnings: list[str]) -> Multiplicity:
    if not text:
        warnings.append(f"Falta la multiplicidad en {where}: se asumió {_DEFAULT_MULTIPLICITY}.")
        text = _DEFAULT_MULTIPLICITY
    try:
        return parse_multiplicity(text.strip())
    except ValueError:
        warnings.append(f"Multiplicidad no válida '{text}' en {where}: se asumió {_DEFAULT_MULTIPLICITY}.")
        return parse_multiplicity(_DEFAULT_MULTIPLICITY)


def _build(raw: _Raw) -> tuple[CanonicalUmlModel, DiagramLayout, list[str]]:
    warnings = list(raw.warnings)
    ids = {c.xid: ElementId(new_id()) for c in raw.classes}
    enum_ids = {c.xid: ids[c.xid] for c in raw.classes if c.literals is not None}
    enum_names = {c.name: ids[c.xid] for c in raw.classes if c.literals is not None}
    class_refs = {c.xid for c in raw.classes if c.literals is None} | {
        c.name for c in raw.classes if c.literals is None
    }

    enumerations = tuple(
        Enumeration(id=ids[c.xid], name=c.name, literals=tuple(EnumerationLiteral(new_id(), n) for n in c.literals))
        for c in raw.classes
        if c.literals is not None
    )
    classes = []
    for c in (c for c in raw.classes if c.literals is None):
        attributes = []
        for attribute in c.attributes:
            if attribute.upper not in (None, "", "1"):
                warnings.append(
                    f"El atributo '{c.name}.{attribute.name}' es multivaluado: se importó como valor único."
                )
            attr_type = _resolve_type(attribute, c.name, raw, enum_ids, enum_names, class_refs, warnings)
            if attr_type is not None:
                attributes.append(
                    UmlAttribute(
                        new_id(), attribute.name, attr_type, _visibility(attribute.visibility) or Visibility.PRIVATE
                    )
                )
        operations = tuple(
            UmlOperation(new_id(), name, visibility=_visibility(vis) or Visibility.PUBLIC)
            for name, vis, _sig in c.operations
        )
        if any(sig for _n, _v, sig in c.operations):
            warnings.append(f"Los parámetros y tipos de retorno de las operaciones de '{c.name}' no se importan.")
        classes.append(
            UmlClass(ids[c.xid], c.name, tuple(attributes), operations, _visibility(c.visibility) or Visibility.PUBLIC)
        )

    relationships = _build_relationships(raw, ids, {c.xid for c in raw.classes if c.literals is None}, warnings)
    model = CanonicalUmlModel(classes=tuple(classes), enumerations=enumerations, relationships=tuple(relationships))
    class_ids = {c.id for c in classes}
    positions = {
        ids[xid]: Position(x=x, y=y) for xid, (x, y) in raw.positions.items() if xid in ids and ids[xid] in class_ids
    }
    return model, DiagramLayout(positions=positions), warnings


def _build_relationships(
    raw: _Raw, ids: dict[str, ElementId], class_xids: set[str], warnings: list[str]
) -> list[Relationship]:
    relationships: list[Relationship] = []
    for child, parent in raw.generalizations:
        if child in class_xids and parent in class_xids:
            one = Multiplicity(1, 1)
            relationships.append(
                Relationship(new_id(), RelationshipKind.GENERALIZATION, RelationshipEnd(ids[child], one), RelationshipEnd(ids[parent], one))
            )
        else:
            warnings.append("Se ignoró una generalización cuyos extremos no son clases soportadas.")
    for association in raw.associations:
        label = f"la asociación '{association.name or 'sin nombre'}'"
        if len(association.ends) != 2 or any(e.class_ref not in class_xids for e in association.ends):
            warnings.append(f"Se ignoró {label}: no conecta exactamente dos clases soportadas.")
            continue
        first, second = association.ends
        source, target, kind = first, second, RelationshipKind.ASSOCIATION
        if first.whole or second.whole:
            source, target = (first, second) if first.whole else (second, first)
            kind = source.kind
        relationships.append(
            Relationship(
                new_id(),
                kind,
                RelationshipEnd(ids[source.class_ref], _multiplicity(source.multiplicity, label, warnings), source.role),
                RelationshipEnd(ids[target.class_ref], _multiplicity(target.multiplicity, label, warnings), target.role),
                association.name,
            )
        )
    return relationships


# --- entry point ----------------------------------------------------------------------


def import_xmi(data: bytes) -> ImportResult:
    """Parse EA XMI bytes into a canonical model. Raises `InvalidXmiError` /
    `UnsupportedXmiError`; everything recoverable becomes a warning.
    """
    if len(data) > MAX_XMI_BYTES:
        raise InvalidXmiError("El archivo supera el máximo permitido de 5 MB.")
    try:
        root = fromstring(data)
    except (ParseError, DefusedXmlException, ValueError) as exc:
        raise InvalidXmiError(f"El archivo no es un XML válido o contiene construcciones no permitidas: {exc}") from exc

    raw = _Raw()
    if _local(root.tag) == "XMI" and _kid(root, "XMI.content") is not None:
        _read_v1(root, raw)
    elif _local(root.tag) in ("XMI", "Model") and any(_local(n.tag) == "packagedElement" for n in root.iter()):
        _read_v2(root, raw)
    else:
        raise UnsupportedXmiError("El archivo no es un XMI 1.1 (UML 1.3) ni un XMI 2.x reconocible.")

    model, layout, warnings = _build(raw)
    if not model.classes:
        raise UnsupportedXmiError("El XMI no contiene clases UML importables.")
    warnings += [f"Validación: {d.message}" for d in validate(model).diagnostics]
    return ImportResult(model, layout, tuple(warnings), raw.diagram_name or raw.package_name)
