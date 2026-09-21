"""Service + HTTP tests for backend deployments, driven by a fake runner client."""
import datetime
from uuid import uuid4

import pytest

from apps.backend_deployments import service
from apps.backend_deployments.models import Deployment, DeploymentStatus
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services as document_services
from apps.uml_modeling.documents import ProjectDocument

_REAL_BUILD_ARCHIVE = service.build_project_archive


def _api(organization, doc_id, suffix="deployments") -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/{suffix}"


def _doc_with_class(client, organization, user, name="Sales Demo") -> str:
    client.force_login(user)
    doc_id = client.post(
        f"/api/orgs/{organization.slug}/documents", data={"name": name}, content_type="application/json"
    ).json()["id"]
    base = f"/api/orgs/{organization.slug}/documents/{doc_id}/commands"
    client.post(base, data={"type": "AddClass", "class_id": "c1", "name": "Order"}, content_type="application/json")
    return doc_id


def _empty_doc(client, organization, user) -> str:
    client.force_login(user)
    return client.post(
        f"/api/orgs/{organization.slug}/documents", data={"name": "Empty"}, content_type="application/json"
    ).json()["id"]


@pytest.mark.django_db
class TestService:
    def _document(self, organization, owner) -> ProjectDocument:
        # The archive builder is stubbed in these tests, so an empty model is enough.
        return document_services.create_document(
            organization=organization, owner_id=str(owner.id), name="Svc Demo",
            now=datetime.datetime.now(datetime.UTC),
        )

    def test_start_uploads_the_zip_and_replaces_the_active_deployment(self, fake_runner, monkeypatch):
        organization, owner, *_ = make_org_with_roles()
        document = self._document(organization, owner)
        monkeypatch.setattr(service, "build_project_archive", lambda doc: b"zip-bytes")

        first = service.start_deployment(organization=organization, document=document, user=owner)
        second = service.start_deployment(organization=organization, document=document, user=owner)

        first.refresh_from_db()
        assert first.status == DeploymentStatus.STOPPED and fake_runner.stopped == [str(first.id)]
        assert second.status == DeploymentStatus.BUILDING
        assert fake_runner.started[-1] == (str(second.id), organization.slug, b"zip-bytes")

    def test_quota_counts_other_documents_only(self, fake_runner, monkeypatch, settings):
        settings.DEPLOYMENT_MAX_ACTIVE_PER_ORG = 1
        organization, owner, *_ = make_org_with_roles()
        monkeypatch.setattr(service, "build_project_archive", lambda doc: b"z")
        doc_a = self._document(organization, owner)
        doc_b = self._document(organization, owner)
        service.start_deployment(organization=organization, document=doc_a, user=owner)

        service.start_deployment(organization=organization, document=doc_a, user=owner)  # replace: ok
        with pytest.raises(service.QuotaExceededError):
            service.start_deployment(organization=organization, document=doc_b, user=owner)

    def test_unreachable_runner_saves_a_failed_row(self, fake_runner, monkeypatch):
        organization, owner, *_ = make_org_with_roles()
        document = self._document(organization, owner)
        monkeypatch.setattr(service, "build_project_archive", lambda doc: b"z")
        fake_runner.down = True

        with pytest.raises(service.DeploymentStartFailed):
            service.start_deployment(organization=organization, document=document, user=owner)

        row = Deployment.objects.for_organization(organization).get()
        assert row.status == DeploymentStatus.FAILED and "unreachable" in row.error

    @pytest.mark.parametrize(
        "runner_state, expected",
        [
            ({"status": "running", "log_tail": "ok", "public_path": "/gen/x/"}, DeploymentStatus.RUNNING),
            ({"status": "failed", "error": "build failed"}, DeploymentStatus.FAILED),
            (None, DeploymentStatus.STOPPED),  # runner lost it (restart / TTL)
        ],
    )
    def test_latest_pulls_the_runner_state(self, fake_runner, monkeypatch, runner_state, expected):
        organization, owner, *_ = make_org_with_roles()
        document = self._document(organization, owner)
        monkeypatch.setattr(service, "build_project_archive", lambda doc: b"z")
        deployment = service.start_deployment(organization=organization, document=document, user=owner)
        fake_runner.states[str(deployment.id)] = runner_state

        latest = service.latest_deployment(organization=organization, doc_id=document.id)

        assert latest.status == expected


@pytest.mark.django_db
class TestApi:
    @pytest.fixture(autouse=True)
    def _archive(self, monkeypatch):
        monkeypatch.setattr(service, "build_project_archive", lambda doc: b"zip")

    def test_start_latest_and_delete_round_trip(self, auth_client, fake_runner):
        organization, owner, *_ = make_org_with_roles()
        doc_id = _doc_with_class(auth_client, organization, owner)

        started = auth_client.post(_api(organization, doc_id))
        assert started.status_code == 202
        body = started.json()
        assert body["status"] == "building" and body["public_path"] == f"/gen/{body['id']}/"
        assert body["public_url"].endswith(f"/gen/{body['id']}/")

        fake_runner.states[body["id"]] = {"status": "running", "public_path": body["public_path"]}
        latest = auth_client.get(_api(organization, doc_id, "deployments/latest"))
        assert latest.status_code == 200 and latest.json()["status"] == "running"

        deleted = auth_client.delete(_api(organization, doc_id, f"deployments/{body['id']}"))
        assert deleted.status_code == 200 and deleted.json()["status"] == "stopped"
        assert fake_runner.stopped == [body["id"]]

    def test_quota_exceeded_is_409_with_code(self, auth_client, fake_runner, settings):
        settings.DEPLOYMENT_MAX_ACTIVE_PER_ORG = 1
        organization, owner, *_ = make_org_with_roles()
        first = _doc_with_class(auth_client, organization, owner, "One")
        second = _doc_with_class(auth_client, organization, owner, "Two")
        assert auth_client.post(_api(organization, first)).status_code == 202

        response = auth_client.post(_api(organization, second))

        assert response.status_code == 409 and response.json()["code"] == "quota_exceeded"

    def test_document_without_classes_is_422(self, auth_client, fake_runner, monkeypatch):
        monkeypatch.setattr(service, "build_project_archive", _REAL_BUILD_ARCHIVE)
        organization, owner, *_ = make_org_with_roles()
        doc_id = _empty_doc(auth_client, organization, owner)

        response = auth_client.post(_api(organization, doc_id))

        assert response.status_code == 422 and response.json()["code"] == "nothing_to_generate"
        assert fake_runner.started == []

    def test_runner_down_is_502(self, auth_client, fake_runner):
        organization, owner, *_ = make_org_with_roles()
        doc_id = _doc_with_class(auth_client, organization, owner)
        fake_runner.down = True

        response = auth_client.post(_api(organization, doc_id))

        assert response.status_code == 502 and response.json()["code"] == "runner_unavailable"

    def test_other_organizations_and_viewers_are_locked_out(self, auth_client, fake_runner):
        organization, owner, _editor, viewer, outsider = make_org_with_roles()
        other_org, other_owner, *_ = make_org_with_roles()
        doc_id = _doc_with_class(auth_client, organization, owner)
        deployment_id = auth_client.post(_api(organization, doc_id)).json()["id"]

        auth_client.force_login(viewer)  # read yes, write no
        assert auth_client.get(_api(organization, doc_id, "deployments/latest")).status_code == 200
        assert auth_client.post(_api(organization, doc_id)).status_code == 403

        auth_client.force_login(outsider)  # not a member
        assert auth_client.get(_api(organization, doc_id, "deployments/latest")).status_code == 404

        auth_client.force_login(other_owner)  # member of ANOTHER org: document is invisible
        assert auth_client.get(_api(other_org, doc_id, "deployments/latest")).status_code == 404
        assert auth_client.delete(_api(other_org, doc_id, f"deployments/{deployment_id}")).status_code == 404

    def test_anonymous_gets_401(self, auth_client):
        organization, *_ = make_org_with_roles()
        assert auth_client.post(_api(organization, uuid4())).status_code == 401
