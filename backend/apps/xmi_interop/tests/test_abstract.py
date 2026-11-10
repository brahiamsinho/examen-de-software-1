"""Abstract classes in XMI: written as `isAbstract="true"`, read back, and read from other tools' files."""
import datetime
import uuid
from xml.etree.ElementTree import fromstring

from apps.uml_modeling.documents import DiagramLayout, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import UmlClass
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.xmi_interop.exporter import export_xmi
from apps.xmi_interop.importer import import_xmi

NOW = datetime.datetime(2026, 9, 20, 12, 0, tzinfo=datetime.timezone.utc)


def _document(*classes) -> ProjectDocument:
    return ProjectDocument(
        id=uuid.uuid4(), metadata=ProjectMetadata(name="Demo"), owner_id="u1",
        model=CanonicalUmlModel(classes=tuple(classes)), layout=DiagramLayout(), created_at=NOW, updated_at=NOW,
    )


def _class_flags(data: bytes) -> dict[str, str]:
    root = fromstring(data)
    return {
        el.get("name"): el.get("isAbstract")
        for el in root.iter()
        if el.tag.rsplit("}", 1)[-1] == "Class" and el.get("name") in {"Shape", "Order"}
    }


def test_the_export_marks_only_the_abstract_class():
    data = export_xmi(_document(UmlClass(new_id(), "Shape", is_abstract=True), UmlClass(new_id(), "Order")))

    assert _class_flags(data) == {"Shape": "true", "Order": "false"}


def test_an_exported_abstract_class_is_still_abstract_after_importing_it_again():
    data = export_xmi(_document(UmlClass(new_id(), "Shape", is_abstract=True), UmlClass(new_id(), "Order")))

    model = import_xmi(data).model

    assert {c.name: c.is_abstract for c in model.classes} == {"Shape": True, "Order": False}


def _ea11(attributes: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="windows-1252"?>'
        '<XMI xmi.version="1.1" xmlns:UML="omg.org/UML1.3"><XMI.content>'
        '<UML:Model name="M" xmi.id="m"><UML:Namespace.ownedElement>'
        f'<UML:Class name="Shape" xmi.id="c1" isAbstract="{attributes}"/>'
        "</UML:Namespace.ownedElement></UML:Model></XMI.content></XMI>"
    ).encode("cp1252")


def test_an_enterprise_architect_file_with_an_abstract_class_is_read_as_abstract():
    assert import_xmi(_ea11("true")).model.classes[0].is_abstract is True
    assert import_xmi(_ea11("false")).model.classes[0].is_abstract is False


def test_a_uml_2_xmi_file_with_an_abstract_class_is_read_as_abstract():
    xmi21 = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<xmi:XMI xmi:version="2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1" '
        'xmlns:uml="http://schema.omg.org/spec/UML/2.1">'
        '<uml:Model xmi:type="uml:Model" xmi:id="m" name="M">'
        '<packagedElement xmi:type="uml:Class" xmi:id="c1" name="Shape" isAbstract="true"/>'
        "</uml:Model></xmi:XMI>"
    ).encode("utf-8")

    assert import_xmi(xmi21).model.classes[0].is_abstract is True
