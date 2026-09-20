"""End-to-end: a profile authored through the real HTTP endpoint survives
persistence and is read back by `map_to_relational` as `Table.profile` /
`Column.profile`; clearing it maps back to `None` (design.md DD152, DD157).

Deliberate test-only import of `apps.relational_mapping`: production code
under `uml_documents` may not depend on it (DD154), but a test is the
seam where both halves meet.
"""
import pytest

from apps.organizations.tests.factories import make_org_with_roles
from apps.relational_mapping.domain.profile import (
    ColumnProfile,
    CrudOperation,
    DefaultSort,
    SortDirection,
    TableProfile,
)
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.uml_documents import codec
from apps.uml_documents.models import UmlDocument


def _post(auth_client, url, data):
    return auth_client.post(url, data=data, content_type="application/json")


def _seed_vehicle_hierarchy(auth_client, editor, organization):
    """root `Vehicle`(a-root) <- child `Car`(a-child); returns the commands URL and doc id."""
    auth_client.force_login(editor)
    doc_id = _post(
        auth_client, f"/api/orgs/{organization.slug}/documents", {"name": "Fleet"}
    ).json()["id"]
    url = f"/api/orgs/{organization.slug}/documents/{doc_id}/commands"
    for class_id, name in (("c-root", "Vehicle"), ("c-child", "Car")):
        _post(auth_client, url, {"type": "AddClass", "class_id": class_id, "name": name})
    for class_id, attribute_id, name in (
        ("c-root", "a-root", "plate"),
        ("c-child", "a-child", "doors"),
    ):
        _post(
            auth_client,
            url,
            {
                "type": "AddAttribute",
                "class_id": class_id,
                "attribute": {"id": attribute_id, "name": name, "type": "String"},
            },
        )
    _post(
        auth_client,
        url,
        {
            "type": "AddRelationship",
            "relationship": {
                "id": "gen-1",
                "kind": "generalization",
                "source": {"class_id": "c-child", "multiplicity": "1"},
                "target": {"class_id": "c-root", "multiplicity": "1"},
            },
        },
    )
    return url, doc_id


def _relational_model(doc_id):
    _metadata, model, _layout = codec.from_json(UmlDocument.all_objects.get(id=doc_id).data)
    return map_to_relational(model)


def _root_table(relational_model):
    return next(table for table in relational_model.tables if "c-root" in table.source_class_ids)


@pytest.mark.django_db
def test_authored_profiles_round_trip_into_table_and_column_profiles(auth_client):
    organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
    url, doc_id = _seed_vehicle_hierarchy(auth_client, editor, organization)

    table_response = _post(
        auth_client,
        url,
        {
            "type": "SetGenerationProfile",
            "element_id": "c-root",
            "profile": {
                "entity": True,
                "auditable": True,
                "crud": ["read", "create"],
                "defaultSort": {"attribute": "a-child", "direction": "desc"},
            },
        },
    )
    column_response = _post(
        auth_client,
        url,
        {"type": "SetGenerationProfile", "element_id": "a-root", "profile": {"searchable": True}},
    )

    assert table_response.status_code == 200
    assert column_response.status_code == 200
    table = _root_table(_relational_model(doc_id))
    # STI: the root's profile becomes the single table's profile, and its
    # defaultSort may point at a descendant-owned attribute (DD157).
    assert table.profile == TableProfile(
        entity=True,
        auditable=True,
        crud=(CrudOperation.CREATE, CrudOperation.READ),
        default_sort=DefaultSort(attribute_id="a-child", direction=SortDirection.DESC),
    )
    column = next(column for column in table.columns if column.source_element_id == "a-root")
    assert column.profile == ColumnProfile(searchable=True)


@pytest.mark.django_db
def test_clearing_the_profile_maps_back_to_none(auth_client):
    organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
    url, doc_id = _seed_vehicle_hierarchy(auth_client, editor, organization)
    _post(
        auth_client,
        url,
        {"type": "SetGenerationProfile", "element_id": "c-root", "profile": {"entity": True}},
    )
    _post(
        auth_client,
        url,
        {"type": "SetGenerationProfile", "element_id": "a-root", "profile": {"sortable": True}},
    )

    _post(auth_client, url, {"type": "SetGenerationProfile", "element_id": "c-root"})
    _post(
        auth_client,
        url,
        {"type": "SetGenerationProfile", "element_id": "a-root", "profile": {}},
    )

    table = _root_table(_relational_model(doc_id))
    assert table.profile is None
    column = next(column for column in table.columns if column.source_element_id == "a-root")
    assert column.profile is None
    assert UmlDocument.all_objects.get(id=doc_id).data["model"]["generation_metadata"] == {}


@pytest.mark.django_db
def test_removing_the_descendant_keeps_the_root_mappable_after_cascade(auth_client):
    organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
    url, doc_id = _seed_vehicle_hierarchy(auth_client, editor, organization)
    _post(
        auth_client,
        url,
        {
            "type": "SetGenerationProfile",
            "element_id": "c-root",
            "profile": {"defaultSort": {"attribute": "a-child", "direction": "asc"}},
        },
    )

    _post(auth_client, url, {"type": "RemoveClass", "class_id": "c-child"})

    table = _root_table(_relational_model(doc_id))
    assert table.profile is None
    assert UmlDocument.all_objects.get(id=doc_id).data["model"]["generation_metadata"] == {}
