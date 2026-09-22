"""Structural checks on the Gemini function-declaration schema: every
declared function name matches what `translator.py` actually handles, and
the `attribute_type`/`return_type` enums never silently drift from the
domain's real closed `PrimitiveType` set.
"""
from apps.ai_assistant import tools
from apps.ai_assistant.translator import _HANDLERS
from apps.uml_modeling.domain.types import PrimitiveType


def test_every_declared_tool_has_a_translator_handler():
    declared_names = {tool["name"] for tool in tools.TOOLS}

    assert declared_names == set(_HANDLERS.keys())


def test_tool_names_are_unique():
    names = [tool["name"] for tool in tools.TOOLS]

    assert len(names) == len(set(names))


def test_every_tool_declares_the_required_shape():
    for tool in tools.TOOLS:
        assert isinstance(tool["name"], str) and tool["name"]
        assert isinstance(tool["description"], str) and tool["description"]
        assert tool["parameters"]["type"] == "object"
        required = tool["parameters"]["required"]
        properties = tool["parameters"]["properties"]
        assert set(required).issubset(properties.keys())


def test_attribute_type_enum_matches_the_domain_primitive_types():
    expected = {member.value for member in PrimitiveType}

    assert set(tools.ADD_ATTRIBUTE["parameters"]["properties"]["attribute_type"]["enum"]) == expected
    assert set(tools.ADD_OPERATION["parameters"]["properties"]["return_type"]["enum"]) == expected


def test_relationship_kind_enum_matches_the_four_uml_kinds():
    expected = {"association", "aggregation", "composition", "generalization"}

    assert set(tools.ADD_RELATIONSHIP["parameters"]["properties"]["kind"]["enum"]) == expected
