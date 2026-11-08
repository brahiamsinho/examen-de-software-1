"""HTTP tests for the diagram session log (issue #17)."""
import datetime

import pytest
from django.utils import timezone

from apps.organizations.tests.factories import make_org_with_roles
from apps.session_log import services as log
from apps.session_log.models import LogKind
from apps.uml_documents import services

_T0 = datetime.datetime(2026, 11, 7, 10, 0, tzinfo=datetime.timezone.utc)


def _document(organization, owner):
    return services.create_document(organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now())


def _url(organization, doc_id, suffix="") -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/log{suffix}"


def _record(organization, document, actor, minute, summary, **extra):
    return log.record(
        organization=organization,
        document_id=document.id,
        kind=extra.pop("kind", LogKind.CHANGE),
        actor=actor,
        summary=summary,
        now=_T0 + datetime.timedelta(minutes=minute),
        **extra,
    )


@pytest.mark.django_db
class TestLogApi:
    def test_every_member_reads_the_log_including_a_viewer(self, auth_client):
        organization, owner, editor, viewer, _outsider = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, editor, 0, "Added class 'A'", data={"commands": [{"type": "AddClass", "label": "A"}]})

        auth_client.force_login(viewer)
        response = auth_client.get(_url(organization, document.id))

        assert response.status_code == 200
        (entry,) = response.json()
        assert entry["author"] == (editor.full_name or editor.email)
        assert entry["author_id"] == str(editor.id)
        assert entry["session"] == 1 and entry["kind"] == "change" and entry["is_ai"] is False
        assert entry["summary"] == "Added class 'A'"
        assert entry["data"] == {"commands": [{"type": "AddClass", "label": "A"}]}
        assert entry["created_at"] == _T0.isoformat().replace("+00:00", "Z") or entry["created_at"].startswith("2026-11-07T10:00")

    def test_it_filters_by_session_user_and_kind_from_the_query_string(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, 0, "first")
        _record(organization, document, editor, 100, "second", kind=LogKind.CHAT_MESSAGE)
        _record(organization, document, None, 101, "third", is_ai=True)
        auth_client.force_login(owner)

        by_session = auth_client.get(_url(organization, document.id), {"session": 2}).json()
        by_user = auth_client.get(_url(organization, document.id), {"user": str(owner.id)}).json()
        by_ai = auth_client.get(_url(organization, document.id), {"user": "ai"}).json()
        by_kind = auth_client.get(_url(organization, document.id), {"kind": "chat.message"}).json()

        assert [e["summary"] for e in by_session] == ["second", "third"]
        assert [e["summary"] for e in by_user] == ["first"]
        assert [e["summary"] for e in by_ai] == ["third"]
        assert [e["summary"] for e in by_kind] == ["second"]

    def test_the_sessions_endpoint_feeds_the_filters(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, 0, "a")
        _record(organization, document, editor, 100, "b")
        auth_client.force_login(editor)

        response = auth_client.get(_url(organization, document.id, "/sessions"))

        assert response.status_code == 200
        sessions = response.json()
        assert [s["session"] for s in sessions] == [1, 2]
        assert sessions[1]["entries"] == 1
        assert sessions[1]["actors"] == [{"id": str(editor.id), "label": editor.full_name or editor.email, "is_ai": False}]

    def test_the_export_is_a_csv_download_that_respects_the_filters(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, 0, "owner row")
        _record(organization, document, editor, 1, "editor row")
        auth_client.force_login(editor)

        response = auth_client.get(_url(organization, document.id, "/export"), {"user": str(editor.id)})

        assert response.status_code == 200
        assert response["Content-Type"].startswith("text/csv")
        assert "attachment" in response["Content-Disposition"] and ".csv" in response["Content-Disposition"]
        body = response.content.decode()
        assert "editor row" in body and "owner row" not in body

    def test_another_organization_gets_404_everywhere(self, auth_client):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, 0, "secret")
        other, _other_owner, other_editor, *_ = make_org_with_roles()
        auth_client.force_login(other_editor)

        for suffix in ("", "/sessions", "/export"):
            assert auth_client.get(_url(other, document.id, suffix)).status_code == 404

    def test_an_anonymous_client_is_rejected(self, client):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        assert client.get(_url(organization, document.id)).status_code == 401

    @pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
    def test_nothing_can_write_edit_or_delete_the_log_over_http(self, auth_client, method):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        entry = _record(organization, document, owner, 0, "keep me")
        auth_client.force_login(owner)

        for path in (_url(organization, document.id), _url(organization, document.id, f"/{entry.id}")):
            response = getattr(auth_client, method)(path, data={"summary": "x"}, content_type="application/json")
            assert response.status_code in (404, 405)

        assert [e["summary"] for e in auth_client.get(_url(organization, document.id)).json()] == ["keep me"]
