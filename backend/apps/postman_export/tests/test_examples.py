"""Example generation from an OpenAPI schema (spec: Body Example Generation)."""
from apps.postman_export.converter.examples import MAX_DEPTH, example_for, resolve_schema

EMPTY_DOCUMENT: dict = {}


def test_scalar_types_produce_deterministic_typed_values():
    assert example_for({"type": "string"}, EMPTY_DOCUMENT) == "string"
    assert example_for({"type": "integer", "format": "int32"}, EMPTY_DOCUMENT) == 0
    assert example_for({"type": "number"}, EMPTY_DOCUMENT) == 0
    assert example_for({"type": "boolean"}, EMPTY_DOCUMENT) is False


def test_formatted_strings_use_a_valid_shape():
    assert example_for({"type": "string", "format": "uuid"}, EMPTY_DOCUMENT) == "00000000-0000-0000-0000-000000000000"
    assert example_for({"type": "string", "format": "date-time"}, EMPTY_DOCUMENT) == "2024-01-01T00:00:00Z"


def test_enum_uses_its_first_value():
    assert example_for({"type": "string", "enum": ["PENDING", "PAID"]}, EMPTY_DOCUMENT) == "PENDING"
    assert example_for({"type": "string", "enum": ["PAID", "PENDING"]}, EMPTY_DOCUMENT) == "PAID"


def test_array_wraps_one_example_item():
    assert example_for({"type": "array", "items": {"type": "integer"}}, EMPTY_DOCUMENT) == [0]
    assert example_for({"type": "array", "items": {"type": "boolean"}}, EMPTY_DOCUMENT) == [False]


def test_object_maps_each_property_and_nests():
    schema = {
        "type": "object",
        "properties": {"fullName": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}},
    }

    assert example_for(schema, EMPTY_DOCUMENT) == {"fullName": "string", "tags": ["string"]}


def test_ref_is_resolved_against_the_document_components():
    document = {"components": {"schemas": {"Customer": {"type": "object", "properties": {"id": {"type": "string", "format": "uuid"}}}}}}

    assert example_for({"$ref": "#/components/schemas/Customer"}, document) == {"id": "00000000-0000-0000-0000-000000000000"}
    assert resolve_schema({"$ref": "#/components/schemas/Customer"}, document)["type"] == "object"
    assert resolve_schema({"type": "string"}, document) == {"type": "string"}


def test_unknown_schema_yields_none():
    assert example_for({}, EMPTY_DOCUMENT) is None


def test_self_referencing_schema_terminates_at_the_depth_limit():
    document = {
        "components": {
            "schemas": {
                "Node": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "next": {"$ref": "#/components/schemas/Node"}},
                }
            }
        }
    }

    example = example_for({"$ref": "#/components/schemas/Node"}, document)

    assert example["name"] == "string"
    depth = 0
    node = example
    while node is not None:
        assert node["name"] == "string"
        node = node["next"]
        depth += 1
    assert depth == MAX_DEPTH


def test_generation_is_deterministic():
    schema = {"type": "object", "properties": {"a": {"type": "string", "format": "uuid"}, "b": {"type": "number"}}}

    assert example_for(schema, EMPTY_DOCUMENT) == example_for(schema, EMPTY_DOCUMENT)
