"""HTTP tests for `GET /api/orgs/{org_slug}/documents/{doc_id}/join-tables`."""
from uuid import uuid4

import pytest

from apps.organizations.tests.factories import make_org_with_roles


def _create_document(client, organization, user, *, name="Sales Demo") -> str:
    client.force_login(user)
    response = client.post(
        f"/api/orgs/{organization.slug}/documents",
        data={"name": name},
        content_type="application/json",
    )
    return response.json()["id"]


def _add_class(client, organization, doc_id, *, name, class_id):
    client.post(
        f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
        data={"type": "AddClass", "class_id": class_id, "name": name},
        content_type="application/json",
    )


def _add_relationship(client, organization, doc_id, *, relationship_id, source, target, source_mult, target_mult):
    client.post(
        f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
        data={
            "type": "AddRelationship",
            "relationship": {
                "id": relationship_id,
                "kind": "association",
                "source": {"class_id": source, "multiplicity": source_mult},
                "target": {"class_id": target, "multiplicity": target_mult},
            },
        },
        content_type="application/json",
    )


def _url(organization, doc_id) -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/join-tables"


def _preview_url(organization, doc_id) -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/relational-preview"


@pytest.mark.django_db
class TestJoinTables:
    def test_a_both_ends_many_association_reports_its_join_table(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        _add_class(auth_client, organization, doc_id, name="Class A", class_id="a")
        _add_class(auth_client, organization, doc_id, name="Class B", class_id="b")
        _add_relationship(
            auth_client,
            organization,
            doc_id,
            relationship_id="r1",
            source="a",
            target="b",
            source_mult="0..*",
            target_mult="0..*",
        )

        auth_client.force_login(viewer)  # read-only member is enough
        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 200
        [hint] = response.json()
        assert hint["relationship_id"] == "r1"
        assert hint["table_name"] == "class_a_class_b"
        assert set(hint["columns"]) == {"id", "class_a_id", "class_b_id"}

    def test_a_to_one_association_reports_no_join_table(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        _add_class(auth_client, organization, doc_id, name="Class A", class_id="a")
        _add_class(auth_client, organization, doc_id, name="Class B", class_id="b")
        _add_relationship(
            auth_client,
            organization,
            doc_id,
            relationship_id="r1",
            source="a",
            target="b",
            source_mult="1",
            target_mult="0..*",
        )

        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 200
        assert response.json() == []

    def test_a_document_with_no_relationships_reports_no_join_tables(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)

        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 200
        assert response.json() == []

    def test_anonymous_user_gets_401(self, auth_client):
        organization, *_rest = make_org_with_roles()

        response = auth_client.get(_url(organization, uuid4()))

        assert response.status_code == 401

    def test_non_member_gets_404_like_the_document_endpoints(self, auth_client):
        organization, owner, _editor, _viewer, outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)

        auth_client.force_login(outsider)
        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 404


@pytest.mark.django_db
class TestRelationalPreview:
    def test_returns_tables_foreign_keys_and_deterministic_sql_without_writing(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        _add_class(auth_client, organization, doc_id, name="Customer", class_id="customer")
        _add_class(auth_client, organization, doc_id, name="Order", class_id="order")
        _add_relationship(
            auth_client,
            organization,
            doc_id,
            relationship_id="customer-orders",
            source="customer",
            target="order",
            source_mult="1",
            target_mult="0..*",
        )

        document_before = auth_client.get(
            f"/api/orgs/{organization.slug}/documents/{doc_id}"
        ).json()
        auth_client.force_login(viewer)
        first = auth_client.get(_preview_url(organization, doc_id))
        second = auth_client.get(_preview_url(organization, doc_id))

        assert first.status_code == 200
        assert first.json() == second.json()
        body = first.json()
        assert [table["name"] for table in body["tables"]] == ["customer", "order"]
        assert body["tables"][0]["columns"][0] == {
            "name": "id", "type": "UUID", "nullable": False, "primary_key": True
        }
        [foreign_key] = body["tables"][1]["foreign_keys"]
        assert foreign_key["referenced_table"] == "customer"
        assert foreign_key["relationship_id"] == "customer-orders"
        assert 'CREATE TABLE "customer"' in body["sql"]
        assert 'ALTER TABLE "order" ADD CONSTRAINT' in body["sql"]
        assert auth_client.get(f"/api/orgs/{organization.slug}/documents/{doc_id}").json() == document_before

    def test_empty_model_returns_actionable_error(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)

        response = auth_client.get(_preview_url(organization, doc_id))

        assert response.status_code == 422
        assert response.json()["code"] == "empty_model"
        assert "Agrega al menos una clase" in response.json()["detail"]

    def test_non_member_cannot_read_preview(self, auth_client):
        organization, owner, _editor, _viewer, outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)

        auth_client.force_login(outsider)
        response = auth_client.get(_preview_url(organization, doc_id))

        assert response.status_code == 404
