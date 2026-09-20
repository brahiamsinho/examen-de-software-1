"""Entities, operations and subtypes of the sample manifest (spec: Entity Content, CRUD Operations)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from apps.domain_manifest.builder import ManifestError, build_manifest
from apps.domain_manifest.builder.entities import build_entity
from apps.generation_runner.samples.sample_model import build_sample_relational_model
from apps.relational_mapping.domain.schema import Column, EnumType, PrimaryKey, RelationalModel, Table
from apps.relational_mapping.domain.types import ColumnType

ENTITY_KEYS = {
    "name", "table", "resourcePath", "discriminatorColumn", "subtypes",
    "operations", "attributes", "relationships", "uniqueConstraints",
}
PRODUCT_TAG_UNIQUE = [{"name": "uq_product_tag__product_id_tag_id", "columns": ["product_id", "tag_id"]}]
SUBTYPES = [{"name": "Car", "discriminatorValue": "Car"}, {"name": "Truck", "discriminatorValue": "Truck"}]
OPERATIONS = [
    ("create", "POST", "", 201),
    ("findById", "GET", "/{id}", 200),
    ("update", "PUT", "/{id}", 200),
    ("delete", "DELETE", "/{id}", 204),
    ("list", "GET", "", 200),
    ("count", "GET", "/count", 200),
]
# table -> (name, resourcePath, discriminatorColumn, subtypes, uniqueConstraints)
SAMPLE_ENTITIES = [
    ("customer", "Customer", "/api/customers", None, [], []),
    ("purchase", "Purchase", "/api/purchases", None, [], []),
    ("vehicle", "Vehicle", None, "class_type", SUBTYPES, []),
    ("product", "Product", "/api/products", None, [], []),
    ("tag", "Tag", "/api/tags", None, [], []),
    ("product_tag", "ProductTag", "/api/product-tags", None, [], PRODUCT_TAG_UNIQUE),
]


def _entity(table_name):
    return build_entity(build_sample_relational_model().table_by_name(table_name))


@pytest.mark.parametrize(("table", "name", "resource", "discriminator", "subtypes", "unique"), SAMPLE_ENTITIES)
def test_sample_entity_header(table, name, resource, discriminator, subtypes, unique):
    entity = _entity(table)

    assert set(entity) == ENTITY_KEYS
    assert (entity["name"], entity["table"], entity["resourcePath"]) == (name, table, resource)
    assert (entity["discriminatorColumn"], entity["subtypes"], entity["uniqueConstraints"]) == (discriminator, subtypes, unique)


@pytest.mark.parametrize(("table", "name", "resource"), [(row[0], row[1], row[2]) for row in SAMPLE_ENTITIES])
def test_operations_exist_exactly_when_the_entity_has_a_controller(table, name, resource):
    operations = [(op["name"], op["method"], op["path"], op["successStatus"]) for op in _entity(table)["operations"]]

    expected = [(op, method, resource + suffix, status) for op, method, suffix, status in OPERATIONS] if resource else []
    assert operations == expected
    assert (resource is None) == (operations == [])


def test_customer_scenario():
    entity = _entity("customer")
    by_name = {attribute["name"]: attribute for attribute in entity["attributes"]}

    assert entity["resourcePath"] == "/api/customers"
    assert by_name["fullName"]["column"] == "full_name" and by_name["fullName"]["maxLength"] == 255
    assert [attribute["name"] for attribute in entity["attributes"] if attribute["primaryKey"]] == ["id"]


# ---- top level: envelope, enums, ordering, exclusions, rejections (spec: Envelope, Enums, Exclusion) ----
FIXTURE = Path(__file__).resolve().parents[2] / "postman_export" / "tests" / "fixtures" / "api-docs.json"
EXCLUDED_KEYS = ["searchable", "sortable", "defaultSort", "auditable", "readOnly", "aliases", "generation_metadata"]


def _all_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_keys(item)


def _table(name, *columns):
    return Table(name=name, columns=(Column("id", ColumnType.UUID), *columns), primary_key=PrimaryKey(("id",)))


def test_envelope_and_ordering():
    manifest = build_manifest(build_sample_relational_model())

    assert set(manifest) == {"schemaVersion", "entities", "enums"}
    assert manifest["schemaVersion"] == 1 and type(manifest["schemaVersion"]) is int
    assert [entity["name"] for entity in manifest["entities"]] == ["Customer", "Product", "ProductTag", "Purchase", "Tag", "Vehicle"]
    for entity in manifest["entities"]:
        fields = [relationship["field"] for relationship in entity["relationships"]]
        assert fields == sorted(fields)


@pytest.mark.parametrize(
    ("enum_types", "expected"),
    [
        (
            build_sample_relational_model().enum_types,
            [{"name": "PurchaseStatus", "values": [{"value": v, "label": v} for v in ("PENDING", "PAID", "SHIPPED")]}],
        ),
        (
            (EnumType("z_status", ("In Progress", "Done")), EnumType("a_kind", ("X",))),
            [
                {"name": "AKind", "values": [{"value": "X", "label": "X"}]},
                {"name": "ZStatus", "values": [{"value": "IN_PROGRESS", "label": "In Progress"}, {"value": "DONE", "label": "Done"}]},
            ],
        ),
    ],
)
def test_enums_are_sorted_by_name_and_keep_value_order_and_labels(enum_types, expected):
    assert build_manifest(RelationalModel(enum_types=tuple(enum_types)))["enums"] == expected


def test_the_enum_attribute_references_a_listed_enum():
    manifest = build_manifest(build_sample_relational_model())
    referenced = {a["enum"] for e in manifest["entities"] for a in e["attributes"] if a["enum"]}

    assert referenced == {"PurchaseStatus"} == {enum["name"] for enum in manifest["enums"]}


@pytest.mark.parametrize("key", EXCLUDED_KEYS)
def test_undeclared_facts_are_never_emitted(key):
    keys = list(_all_keys(build_manifest(build_sample_relational_model())))

    assert "resourcePath" in keys and key not in keys  # the scan really walked the tree


@pytest.mark.parametrize(
    "table",
    [_table("1bad"), _table("customer", Column("shape", SimpleNamespace(name="GEOMETRY")))],
)
def test_a_model_the_generator_cannot_name_or_type_is_rejected(table):
    with pytest.raises(ValueError):
        build_manifest(RelationalModel(tables=(table,)))
    assert issubclass(ManifestError, ValueError)


# ---- drift guard (spec: Endpoint Drift Guard, DD129): the springdoc fixture is read-only ----
def test_computed_paths_equal_the_paths_springdoc_served():
    served = set(json.loads(FIXTURE.read_text(encoding="utf-8"))["paths"])
    entities = build_manifest(build_sample_relational_model())["entities"]
    computed = {op["path"] for entity in entities for op in entity["operations"]}
    resources = {entity["resourcePath"] for entity in entities if entity["resourcePath"]}

    assert len(served) == 15 and not any("vehicles" in path for path in served)
    assert computed == served
    assert resources <= computed and len(resources) == 5
