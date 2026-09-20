"""Schema contract: discriminated-union parsing and instantiation shapes
(spec: Command Submission — discriminated-union schema; DD2).
"""
import datetime
import uuid

import pytest
from pydantic import TypeAdapter, ValidationError

from apps.uml_documents import schemas

_command_in_adapter = TypeAdapter(schemas.CommandIn)


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        ({"type": "AddClass", "class_id": "c1", "name": "Order"}, schemas.AddClassIn),
        ({"type": "RemoveClass", "class_id": "c1"}, schemas.RemoveClassIn),
        ({"type": "RenameClass", "class_id": "c1", "new_name": "Renamed"}, schemas.RenameClassIn),
        (
            {
                "type": "AddAttribute",
                "class_id": "c1",
                "attribute": {"id": "a1", "name": "reference", "type": "String"},
            },
            schemas.AddAttributeIn,
        ),
        (
            {"type": "RemoveAttribute", "class_id": "c1", "attribute_id": "a1"},
            schemas.RemoveAttributeIn,
        ),
        (
            {
                "type": "AddOperation",
                "class_id": "c1",
                "operation": {"id": "o1", "name": "crearUsuario", "return_type": "String"},
            },
            schemas.AddOperationIn,
        ),
        (
            {"type": "RemoveOperation", "class_id": "c1", "operation_id": "o1"},
            schemas.RemoveOperationIn,
        ),
        (
            {
                "type": "AddRelationship",
                "relationship": {
                    "id": "r1",
                    "kind": "association",
                    "source": {"class_id": "c1", "multiplicity": "1"},
                    "target": {"class_id": "c2", "multiplicity": "0..*"},
                },
            },
            schemas.AddRelationshipIn,
        ),
        (
            {"type": "RemoveRelationship", "relationship_id": "r1"},
            schemas.RemoveRelationshipIn,
        ),
        (
            {"type": "SetGenerationProfile", "element_id": "c1", "profile": {"entity": True}},
            schemas.SetGenerationProfileIn,
        ),
    ],
)
def test_command_in_discriminates_each_of_the_ten_shapes(payload, expected_type):
    parsed = _command_in_adapter.validate_python(payload)

    assert isinstance(parsed, expected_type)
    assert parsed.type == payload["type"]


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "SetGenerationProfile", "element_id": "c1"},
        {"type": "SetGenerationProfile", "element_id": "c1", "profile": None},
    ],
)
def test_set_generation_profile_in_profile_omitted_or_null_parses_to_none(payload):
    parsed = _command_in_adapter.validate_python(payload)

    assert parsed.profile is None


def test_set_generation_profile_in_empty_profile_stays_an_empty_dict():
    parsed = _command_in_adapter.validate_python(
        {"type": "SetGenerationProfile", "element_id": "c1", "profile": {}}
    )

    assert parsed.profile == {}


def test_set_generation_profile_in_keeps_nested_json_intact():
    profile = {
        "entity": True,
        "crud": ["create", "read"],
        "defaultSort": {"attribute": "a1", "direction": "asc"},
    }

    parsed = _command_in_adapter.validate_python(
        {"type": "SetGenerationProfile", "element_id": "c1", "profile": profile}
    )

    assert parsed.profile == profile


def test_uml_operation_in_return_type_accepts_null():
    parsed = schemas.UmlOperationIn(id="o1", name="crearUsuario", return_type=None)

    assert parsed.return_type is None


def test_uml_operation_in_return_type_defaults_to_none_when_omitted():
    parsed = schemas.UmlOperationIn(id="o1", name="crearUsuario")

    assert parsed.return_type is None


def test_uml_operation_in_return_type_accepts_a_primitive_string():
    parsed = schemas.UmlOperationIn(id="o1", name="crearUsuario", return_type="String")

    assert parsed.return_type == "String"


def test_uml_operation_in_visibility_defaults_to_public():
    parsed = schemas.UmlOperationIn(id="o1", name="crearUsuario")

    assert parsed.visibility == "public"


def test_document_create_in_requires_name():
    schemas.DocumentCreateIn(name="My Diagram")

    with pytest.raises(ValidationError):
        schemas.DocumentCreateIn()


def test_document_out_instantiates_from_services_shaped_dict():
    schemas.DocumentOut(
        id=uuid.uuid4(),
        owner_id="owner-1",
        revision=1,
        metadata={"name": "My Diagram", "description": ""},
        model={"classes": [], "enumerations": [], "relationships": [], "generation_metadata": {}},
        layout={"positions": {}},
        created_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )


def test_command_result_out_instantiates_from_services_shaped_dict():
    schemas.CommandResultOut(
        revision=2,
        validation={
            "is_valid": False,
            "violations": [
                {
                    "severity": "error",
                    "code": "INVALID_RELATIONSHIP_ENDPOINT",
                    "message": "dangling endpoint",
                    "path": "/relationships/r1",
                }
            ],
        },
    )


def test_validation_out_and_diagnostic_out_instantiate_from_services_shaped_dict():
    schemas.ValidationOut(is_valid=True, violations=[])
    schemas.DiagnosticOut(severity="warning", code="EMPTY_ELEMENT_NAME", message="msg", path="/classes/c1")


def test_document_summary_out_serializes_name_flat_not_nested():
    summary = schemas.DocumentSummaryOut(
        id=uuid.uuid4(),
        name="My Diagram",
        revision=3,
        updated_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )

    data = summary.model_dump()

    assert data["name"] == "My Diagram"
    assert "metadata" not in data
    assert "model" not in data
    assert "layout" not in data
