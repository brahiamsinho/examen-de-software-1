"""Entities, operations and subtypes of the sample manifest (spec: Entity Content, CRUD Operations)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from apps.domain_manifest.builder import ManifestError, build_manifest
from apps.domain_manifest.builder.entities import build_entity
from apps.domain_manifest.serialize import to_json_text
from apps.generation_runner.samples.sample_model import build_sample_relational_model
from apps.relational_mapping.domain.profile import ColumnProfile, CrudOperation, DefaultSort, SortDirection, TableProfile
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
EXCLUDED_KEYS = ["aliases", "entity", "generation_metadata"]  # DD148: the five section 33 keys are emitted iff declared


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


def test_manifest_error_lives_in_errors_and_is_re_exported():
    from apps.domain_manifest.builder import errors

    assert errors.ManifestError is ManifestError
    assert issubclass(errors.ManifestError, ValueError)


# ---- drift guard (spec: Endpoint Drift Guard, DD129): the springdoc fixture is read-only ----
def test_computed_paths_equal_the_paths_springdoc_served():
    served = set(json.loads(FIXTURE.read_text(encoding="utf-8"))["paths"])
    entities = build_manifest(build_sample_relational_model())["entities"]
    computed = {op["path"] for entity in entities for op in entity["operations"]}
    resources = {entity["resourcePath"] for entity in entities if entity["resourcePath"]}

    assert len(served) == 15 and not any("vehicles" in path for path in served)
    assert computed == served
    assert resources <= computed and len(resources) == 5


# ---- entity profile and defaultSort (spec: Declared-Facts-Only Emission, Default Sort Attribute Resolution) ----
def _profiled_table(profile, *columns, name="purchase", **table_kwargs):
    return Table(
        name=name,
        columns=(Column("id", ColumnType.UUID), *columns),
        primary_key=PrimaryKey(("id",)),
        profile=profile,
        **table_kwargs,
    )


def _sort_on(attribute_id, direction=SortDirection.DESC):
    return TableProfile(default_sort=DefaultSort(attribute_id=attribute_id, direction=direction))


def _vehicle_table(attribute_id):
    return _profiled_table(
        _sort_on(attribute_id),
        # The discriminator carries an element id too, yet the attributes builder skips it: it must not resolve.
        Column("class_type", ColumnType.VARCHAR, source_element_id="a-class-type"),
        Column("plate", ColumnType.VARCHAR, source_element_id="a-plate", owning_class_id="c-vehicle"),
        Column("doors", ColumnType.INTEGER, nullable=True, source_element_id="a-doors", owning_class_id="c-car"),
        name="vehicle",
        source_class_ids=("c-vehicle", "c-car"),
        discriminator_column="class_type",
        discriminator_values={"c-vehicle": "Vehicle", "c-car": "Car"},
    )


def test_the_entity_profile_is_emitted_last_with_every_declared_key():
    profile = TableProfile(
        auditable=True,
        read_only=False,
        crud=(CrudOperation.CREATE, CrudOperation.READ),
        default_sort=DefaultSort(attribute_id="a-total", direction=SortDirection.DESC),
    )

    entity = build_entity(_profiled_table(profile, Column("total", ColumnType.NUMERIC, source_element_id="a-total")))

    assert entity["profile"] == {
        "auditable": True,
        "readOnly": False,
        "crud": ["create", "read"],
        "defaultSort": {"attribute": "total", "direction": "desc"},
    }
    assert list(entity)[-1] == "profile"


def test_default_sort_resolves_to_the_emitted_camel_case_attribute_name():
    entity = build_entity(_profiled_table(_sort_on("a-1"), Column("full_name", ColumnType.VARCHAR, source_element_id="a-1")))

    assert entity["profile"]["defaultSort"]["attribute"] == "fullName"
    assert entity["profile"]["defaultSort"]["attribute"] in [attribute["name"] for attribute in entity["attributes"]]


def test_default_sort_on_a_subtype_owned_attribute_resolves_on_the_root_entity():
    entity = build_entity(_vehicle_table("a-doors"))

    assert entity["profile"]["defaultSort"]["attribute"] == "doors"
    assert [a["subtype"] for a in entity["attributes"] if a["name"] == "doors"] == ["Car"]


@pytest.mark.parametrize(
    "attribute_id",
    ["attr-x", "a-other-table", "a-class-type"],  # unknown, foreign, discriminator
)
def test_an_unresolvable_default_sort_id_raises_the_exact_error(attribute_id):
    table = _vehicle_table(attribute_id)
    message = f"table 'vehicle' declares defaultSort on unknown attribute id {attribute_id!r}"

    with pytest.raises(ManifestError) as raised:
        build_entity(table)
    assert str(raised.value) == message
    with pytest.raises(ManifestError, match="unknown attribute id"):
        build_manifest(RelationalModel(tables=(table,)))


def test_a_synthetic_column_id_is_unknown():
    table = _profiled_table(_sort_on("id"), Column("total", ColumnType.NUMERIC, source_element_id="a-total"))

    with pytest.raises(ManifestError, match=r"table 'purchase' declares defaultSort on unknown attribute id 'id'"):
        build_entity(table)


def test_the_entity_flag_is_never_emitted_even_when_declared():
    table = _profiled_table(TableProfile(auditable=True, entity=True))

    manifest = build_manifest(RelationalModel(tables=(table,)))

    assert manifest["entities"][0]["profile"] == {"auditable": True}
    assert "entity" not in list(_all_keys(manifest))


def test_the_serialized_profile_is_alphabetical_whatever_the_insertion_order():
    profile = TableProfile(
        auditable=True,
        read_only=False,
        crud=(CrudOperation.CREATE,),
        default_sort=DefaultSort(attribute_id="a-total", direction=SortDirection.ASC),
    )
    table = _profiled_table(profile, Column("total", ColumnType.NUMERIC, source_element_id="a-total"))

    text = to_json_text(build_manifest(RelationalModel(tables=(table,))))
    entity_profile = json.loads(text)["entities"][0]["profile"]

    assert list(entity_profile) == ["auditable", "crud", "defaultSort", "readOnly"]
    assert to_json_text(json.loads(text)) == text


def test_the_schema_version_stays_one_when_profiles_are_declared():
    table = _profiled_table(TableProfile(auditable=True))

    manifest = build_manifest(RelationalModel(tables=(table,)))

    assert manifest["schemaVersion"] == 1 and type(manifest["schemaVersion"]) is int
    assert isinstance(manifest["entities"], list) and isinstance(manifest["enums"], list)


def test_declaring_crud_does_not_filter_the_operations():
    table = _profiled_table(TableProfile(crud=(CrudOperation.READ,)), Column("total", ColumnType.NUMERIC))

    entity = build_entity(table)

    assert entity["profile"]["crud"] == ["read"]
    assert [(op["name"], op["method"], op["path"], op["successStatus"]) for op in entity["operations"]] == [
        (name, method, "/api/purchases" + suffix, status) for name, method, suffix, status in OPERATIONS
    ]


def test_a_profile_carrying_model_serializes_to_identical_bytes_without_an_id_key():
    def build():
        table = _profiled_table(
            TableProfile(
                auditable=True,
                crud=(CrudOperation.CREATE, CrudOperation.READ),
                default_sort=DefaultSort(attribute_id="a-total", direction=SortDirection.DESC),
            ),
            Column("total", ColumnType.NUMERIC, source_element_id="a-total", profile=ColumnProfile(sortable=True)),
        )
        return to_json_text(build_manifest(RelationalModel(tables=(table,))))

    first, second = build(), build()

    assert first == second
    assert "id" not in _all_keys(json.loads(first))
