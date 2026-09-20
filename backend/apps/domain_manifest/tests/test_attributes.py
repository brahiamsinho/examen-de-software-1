"""Attribute derivation (spec: Entity Content, DD125): closed type map and column -> attribute."""
from types import SimpleNamespace

import pytest
from apps.domain_manifest.builder.attributes import attribute_name, build_attributes, neutral_type
from apps.generation_runner.samples.sample_model import build_sample_relational_model
from apps.relational_mapping.domain.profile import ColumnProfile
from apps.relational_mapping.domain.schema import Column, PrimaryKey, Table
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


# ---- column profile (spec: Entity Content, Declared-Facts-Only Emission; DD144, DD145) ----
def _profiled(profile):
    table = Table(
        name="customer",
        columns=(Column("id", ColumnType.UUID), Column("full_name", ColumnType.VARCHAR, length=255, profile=profile)),
        primary_key=PrimaryKey(("id",)),
    )
    return {attribute["name"]: attribute for attribute in build_attributes(table)}["fullName"]


def test_attribute_name_is_the_camel_cased_column_name():
    assert attribute_name(Column("full_name", ColumnType.VARCHAR)) == "fullName"


def test_a_declared_column_profile_is_added_and_the_fixed_keys_are_unchanged():
    profiled = _profiled(ColumnProfile(searchable=True, sortable=True, read_only=False))

    assert profiled["profile"] == {"searchable": True, "sortable": True, "readOnly": False}
    assert {key: value for key, value in profiled.items() if key != "profile"} == _attribute(
        "fullName", "full_name", "string", max_length=255
    )
    assert list(profiled)[-1] == "profile"


def test_a_declared_false_is_still_emitted():
    assert _profiled(ColumnProfile(searchable=False))["profile"] == {"searchable": False}


@pytest.mark.parametrize("profile", [None, ColumnProfile()])
def test_an_absent_or_empty_column_profile_adds_no_key(profile):
    assert "profile" not in _profiled(profile)
