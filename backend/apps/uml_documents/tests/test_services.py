"""Service-layer contract: creation, read, command->domain mapping, and
command submission (design.md's Data Flow; spec's Document Creation,
Document Read, Command Submission requirements).
"""
import datetime

import pytest
from django.http import Http404

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_commands import commands
from apps.uml_documents import schemas, services
from apps.uml_modeling.domain.elements import (
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    Visibility,
)
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity, PrimitiveType
from apps.uml_modeling.validation.diagnostics import DiagnosticCode

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
_LATER = datetime.datetime(2026, 1, 1, 0, 5, tzinfo=datetime.timezone.utc)


@pytest.mark.django_db
def test_create_document():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()

    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    assert document.owner_id == str(owner.id)
    assert document.revision == 1
    assert document.model == CanonicalUmlModel()
    assert document.layout.positions == {}
    assert document.metadata.name == "My Diagram"


@pytest.mark.django_db
def test_get_document():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    other_organization, *_rest = make_org_with_roles()

    created = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    fetched = services.get_document(organization=organization, doc_id=created.id)
    assert fetched == created

    with pytest.raises(Http404):
        services.get_document(organization=other_organization, doc_id=created.id)


@pytest.mark.django_db
def test_list_documents_returns_only_that_org_rows_newest_updated_first():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    other_organization, other_owner, *_rest = make_org_with_roles()

    first = services.create_document(
        organization=organization, owner_id=str(owner.id), name="First", now=_NOW
    )
    third = services.create_document(
        organization=organization,
        owner_id=str(owner.id),
        name="Third",
        now=_NOW + datetime.timedelta(minutes=10),
    )
    second = services.create_document(
        organization=organization,
        owner_id=str(owner.id),
        name="Second",
        now=_LATER,
    )
    services.create_document(
        organization=other_organization, owner_id=str(other_owner.id), name="Other org", now=_NOW
    )

    documents = services.list_documents(organization=organization)

    assert [document.id for document in documents] == [third.id, second.id, first.id]


@pytest.mark.django_db
def test_list_documents_returns_empty_list_for_organization_with_no_documents():
    organization, *_rest = make_org_with_roles()

    documents = services.list_documents(organization=organization)

    assert documents == []


@pytest.mark.django_db
def test_command_from_payload():
    class_id = new_id()
    attribute_id = new_id()
    relationship_id = new_id()
    target_class_id = new_id()

    add_class = services.command_from_payload(
        schemas.AddClassIn(type="AddClass", class_id=class_id, name="Order")
    )
    assert add_class == commands.AddClass(class_id=class_id, name="Order")

    remove_class = services.command_from_payload(
        schemas.RemoveClassIn(type="RemoveClass", class_id=class_id)
    )
    assert remove_class == commands.RemoveClass(class_id=class_id)

    rename_class = services.command_from_payload(
        schemas.RenameClassIn(type="RenameClass", class_id=class_id, new_name="Renamed")
    )
    assert rename_class == commands.RenameClass(class_id=class_id, new_name="Renamed")

    add_attribute = services.command_from_payload(
        schemas.AddAttributeIn(
            type="AddAttribute",
            class_id=class_id,
            attribute=schemas.UmlAttributeIn(
                id=attribute_id, name="reference", type="String", visibility="private"
            ),
        )
    )
    assert add_attribute == commands.AddAttribute(
        class_id=class_id,
        attribute=UmlAttribute(
            id=attribute_id, name="reference", type=PrimitiveType.STRING, visibility=Visibility.PRIVATE
        ),
    )

    remove_attribute = services.command_from_payload(
        schemas.RemoveAttributeIn(
            type="RemoveAttribute", class_id=class_id, attribute_id=attribute_id
        )
    )
    assert remove_attribute == commands.RemoveAttribute(class_id=class_id, attribute_id=attribute_id)

    add_relationship = services.command_from_payload(
        schemas.AddRelationshipIn(
            type="AddRelationship",
            relationship=schemas.RelationshipIn(
                id=relationship_id,
                kind="association",
                source=schemas.RelationshipEndIn(class_id=class_id, multiplicity="1"),
                target=schemas.RelationshipEndIn(class_id=target_class_id, multiplicity="0..*"),
            ),
        )
    )
    assert add_relationship == commands.AddRelationship(
        relationship=Relationship(
            id=relationship_id,
            kind=RelationshipKind.ASSOCIATION,
            source=RelationshipEnd(class_id=class_id, multiplicity=Multiplicity(1, 1)),
            target=RelationshipEnd(class_id=target_class_id, multiplicity=Multiplicity(0, None)),
        )
    )

    remove_relationship = services.command_from_payload(
        schemas.RemoveRelationshipIn(type="RemoveRelationship", relationship_id=relationship_id)
    )
    assert remove_relationship == commands.RemoveRelationship(relationship_id=relationship_id)


@pytest.mark.django_db
def test_submit_command():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    class_id = new_id()
    result_1 = services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_id, name="Order"),
        now=_NOW,
    )
    assert result_1.document.revision == document.revision + 1

    attribute_id = new_id()
    attribute = UmlAttribute(id=attribute_id, name="reference", type=PrimitiveType.STRING)
    result_2 = services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddAttribute(class_id=class_id, attribute=attribute),
        now=_LATER,
    )
    assert result_2.document.revision == result_1.document.revision + 1

    persisted = services.get_document(organization=organization, doc_id=document.id)
    assert persisted.revision == result_2.document.revision
    persisted_class = persisted.model.class_by_id(class_id)
    assert persisted_class is not None
    assert len(persisted_class.attributes) == 1


@pytest.mark.django_db
def test_submit_command_persists_invalid_result_with_diagnostics():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    class_a_id = new_id()
    services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_a_id, name="A"),
        now=_NOW,
    )

    relationship = Relationship(
        id=new_id(),
        kind=RelationshipKind.ASSOCIATION,
        source=RelationshipEnd(class_id=class_a_id, multiplicity=Multiplicity(1, 1)),
        target=RelationshipEnd(class_id=new_id(), multiplicity=Multiplicity(1, 1)),
    )

    result = services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddRelationship(relationship=relationship),
        now=_LATER,
    )

    assert result.validation_result.is_blocking
    codes = {diagnostic.code for diagnostic in result.validation_result.diagnostics}
    assert DiagnosticCode.INVALID_RELATIONSHIP_ENDPOINT in codes

    persisted = services.get_document(organization=organization, doc_id=document.id)
    assert persisted.revision == result.document.revision
    assert len(persisted.model.relationships) == 1
