"""Dependency in XMI: written as a UML Dependency (client -> supplier), read back, and read from other tools."""
import datetime
import uuid
from xml.etree.ElementTree import fromstring

from apps.uml_commands.tests.factories import a_class, a_relationship, a_relationship_end
from apps.uml_modeling.documents import DiagramLayout, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.xmi_interop.exporter import export_xmi
from apps.xmi_interop.importer import import_xmi

NOW = datetime.datetime(2026, 9, 20, 12, 0, tzinfo=datetime.timezone.utc)


def _document(model) -> ProjectDocument:
    return ProjectDocument(
        id=uuid.uuid4(), metadata=ProjectMetadata(name="Demo"), owner_id="u1", model=model,
        layout=DiagramLayout(), created_at=NOW, updated_at=NOW,
    )


def _model():
    client, supplier = a_class(name="Pedido"), a_class(name="Calculadora")
    dependency = a_relationship(
        kind=RelationshipKind.DEPENDENCY,
        source=a_relationship_end(class_id=client.id),
        target=a_relationship_end(class_id=supplier.id),
    )
    return CanonicalUmlModel(classes=(client, supplier), relationships=(dependency,))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def test_the_export_writes_a_uml_dependency_from_the_client_to_the_supplier_and_no_association():
    root = fromstring(export_xmi(_document(_model())))
    ids = {el.get("name"): el.get("xmi.id") for el in root.iter() if _local(el.tag) == "Class" and el.get("name")}
    dependencies = [el for el in root.iter() if _local(el.tag) == "Dependency"]

    assert len(dependencies) == 1
    assert dependencies[0].get("client") == ids["Pedido"]
    assert dependencies[0].get("supplier") == ids["Calculadora"]
    assert [el for el in root.iter() if _local(el.tag) == "Association"] == []


def test_an_exported_dependency_comes_back_as_a_dependency_with_the_same_ends():
    imported = import_xmi(export_xmi(_document(_model()))).model

    (relationship,) = imported.relationships
    names = {c.id: c.name for c in imported.classes}
    assert relationship.kind is RelationshipKind.DEPENDENCY
    assert (names[relationship.source.class_id], names[relationship.target.class_id]) == ("Pedido", "Calculadora")


def test_an_enterprise_architect_file_with_a_dependency_is_read_as_one():
    ea = (
        '<?xml version="1.0" encoding="windows-1252"?>'
        '<XMI xmi.version="1.1" xmlns:UML="omg.org/UML1.3"><XMI.content>'
        '<UML:Model name="M" xmi.id="m"><UML:Namespace.ownedElement>'
        '<UML:Class name="Pedido" xmi.id="c1"/><UML:Class name="Calculadora" xmi.id="c2"/>'
        '<UML:Dependency xmi.id="d1" client="c1" supplier="c2"/>'
        "</UML:Namespace.ownedElement></UML:Model></XMI.content></XMI>"
    ).encode("cp1252")

    (relationship,) = import_xmi(ea).model.relationships

    assert relationship.kind is RelationshipKind.DEPENDENCY


def test_a_uml_2_xmi_file_with_a_dependency_is_read_as_one():
    xmi21 = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<xmi:XMI xmi:version="2.1" xmlns:xmi="http://schema.omg.org/spec/XMI/2.1" '
        'xmlns:uml="http://schema.omg.org/spec/UML/2.1">'
        '<uml:Model xmi:type="uml:Model" xmi:id="m" name="M">'
        '<packagedElement xmi:type="uml:Class" xmi:id="c1" name="Pedido"/>'
        '<packagedElement xmi:type="uml:Class" xmi:id="c2" name="Calculadora"/>'
        '<packagedElement xmi:type="uml:Dependency" xmi:id="d1" client="c1" supplier="c2"/>'
        "</uml:Model></xmi:XMI>"
    ).encode("utf-8")

    (relationship,) = import_xmi(xmi21).model.relationships

    assert relationship.kind is RelationshipKind.DEPENDENCY


def test_a_dependency_with_a_missing_end_is_skipped_not_a_crash():
    ea = (
        '<?xml version="1.0" encoding="windows-1252"?>'
        '<XMI xmi.version="1.1" xmlns:UML="omg.org/UML1.3"><XMI.content>'
        '<UML:Model name="M" xmi.id="m"><UML:Namespace.ownedElement>'
        '<UML:Class name="Pedido" xmi.id="c1"/>'
        '<UML:Dependency xmi.id="d1" client="c1" supplier="ghost"/>'
        "</UML:Namespace.ownedElement></UML:Model></XMI.content></XMI>"
    ).encode("cp1252")

    assert import_xmi(ea).model.relationships == ()
