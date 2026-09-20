"""Attribute derivation (spec: Entity Content, DD125): closed type map and column -> attribute."""
from types import SimpleNamespace

import pytest
from apps.domain_manifest.builder.attributes import build_attributes, neutral_type
from apps.generation_runner.samples.sample_model import build_sample_relational_model
from apps.relational_mapping.domain.types import ColumnType

TYPE_MAP = {
    ColumnType.UUID: "uuid",
    ColumnType.VARCHAR: "string",
    ColumnType.TEXT: "text",
    ColumnType.INTEGER: "integer",
    ColumnType.BIGINT: "long",
    ColumnType.NUMERIC: "decimal",
    ColumnType.BOOLEAN: "boolean",
    ColumnType.DATE: "date",
    ColumnType.TIMESTAMPTZ: "datetime",
    ColumnType.ENUM: "enum",
}


def _attribute(name, column, type_, *, required=True, primary_key=False, max_length=None, enum=None, subtype=None):
    return {
        "name": name, "column": column, "type": type_, "required": required, "primaryKey": primary_key,
        "maxLength": max_length, "enum": enum, "subtype": subtype,
    }


SAMPLE_ATTRIBUTES = [
    ("customer", _attribute("id", "id", "uuid", primary_key=True)),
    ("customer", _attribute("fullName", "full_name", "string", max_length=255)),
    ("purchase", _attribute("total", "total", "decimal")),
    ("purchase", _attribute("status", "status", "enum", enum="PurchaseStatus")),
    ("purchase", _attribute("placedAt", "placed_at", "datetime")),
    ("purchase", _attribute("gift", "gift", "boolean")),
    ("purchase", _attribute("itemCount", "item_count", "integer")),
    ("purchase", _attribute("notes", "notes", "text")),
    ("purchase", _attribute("customerId", "customer_id", "uuid")),
    ("vehicle", _attribute("plate", "plate", "string", max_length=255)),
    ("vehicle", _attribute("doors", "doors", "integer", required=False, subtype="Car")),
    ("vehicle", _attribute("payload", "payload", "decimal", required=False, subtype="Truck")),
]


def _table(name):
    return build_sample_relational_model().table_by_name(name)


def test_the_type_map_covers_every_column_type():
    assert set(TYPE_MAP) == set(ColumnType)


@pytest.mark.parametrize(("column_type", "neutral"), list(TYPE_MAP.items()))
def test_neutral_type_names(column_type, neutral):
    assert neutral_type(column_type) == neutral


def test_an_unknown_column_type_is_rejected():
    with pytest.raises(ValueError, match="GEOMETRY"):
        neutral_type(SimpleNamespace(name="GEOMETRY"))


@pytest.mark.parametrize(("table", "expected"), SAMPLE_ATTRIBUTES)
def test_sample_attribute(table, expected):
    by_name = {attribute["name"]: attribute for attribute in build_attributes(_table(table))}

    assert by_name[expected["name"]] == expected


@pytest.mark.parametrize(
    ("table", "names"),
    [
        ("customer", ["id", "fullName"]),
        ("vehicle", ["id", "plate", "doors", "payload"]),
    ],
)
def test_attributes_keep_column_order_and_skip_the_discriminator(table, names):
    assert [attribute["name"] for attribute in build_attributes(_table(table))] == names
