"""The two events that trigger a push: a new AI draft and a change to a diagram."""
import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.ai_assistant import proposals
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.notifications import service
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import schemas, services


class _FakeClient:
    def __init__(self, calls):
        self._calls = calls

    def generate_function_calls(self, **_kwargs):
        return self._calls


@pytest.fixture(autouse=True)
def recorder(monkeypatch):
    cache.clear()
    sent = []
    monkeypatch.setattr(service, "notify_organization", lambda **kwargs: sent.append(kwargs))
    return sent


def _document(organization, owner):
    return services.create_document(
        organization=organization, owner_id=str(owner.id), name="Ventas", now=timezone.now()
    )


def _add_class(organization, doc_id, name):
    command = services.command_from_payload(schemas.AddClassIn(type="AddClass", class_id=f"id-{name}", name=name))
    return services.submit_commands(
        organization=organization, doc_id=doc_id, commands_to_apply=[command], now=timezone.now()
    )


@pytest.mark.django_db
class TestNewProposal:
    def test_a_new_draft_notifies_the_organization_except_who_asked(self, recorder, django_capture_on_commit_callbacks):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        recorder.clear()

        with django_capture_on_commit_callbacks(execute=True):
            proposals.create_proposal(
                organization=organization,
                doc_id=document.id,
                requested_by=editor,
                prompt="falta algo?",
                gemini=_FakeClient([GeminiFunctionCall(name="add_class", args={"name": "Pedido"})]),
            )

        [sent] = recorder
        assert sent["organization_id"] == organization.id
        assert sent["exclude_user_id"] == editor.id
        assert sent["data"]["type"] == "proposal"
        assert sent["data"]["document_id"] == str(document.id)
        assert sent["data"]["organization_slug"] == organization.slug
        assert "Ventas" in sent["body"]

    def test_a_draft_that_changes_nothing_notifies_nobody(self, recorder, django_capture_on_commit_callbacks):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _add_class(organization, document.id, "Pedido")
        recorder.clear()

        with django_capture_on_commit_callbacks(execute=True), pytest.raises(proposals.NoSuggestionsError):
            proposals.create_proposal(
                organization=organization,
                doc_id=document.id,
                requested_by=editor,
                prompt="x",
                gemini=_FakeClient([GeminiFunctionCall(name="add_class", args={"name": "Pedido"})]),
            )

        assert recorder == []


@pytest.mark.django_db
class TestDiagramChange:
    def test_a_change_notifies_the_organization(self, recorder, django_capture_on_commit_callbacks):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        recorder.clear()
        cache.clear()

        with django_capture_on_commit_callbacks(execute=True):
            _add_class(organization, document.id, "Pedido")

        [sent] = recorder
        assert sent["organization_id"] == organization.id
        assert sent["data"]["type"] == "document"
        assert sent["data"]["document_id"] == str(document.id)
        assert "Ventas" in sent["body"]

    def test_a_burst_of_changes_sends_a_single_push(self, recorder, django_capture_on_commit_callbacks):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        recorder.clear()
        cache.clear()

        with django_capture_on_commit_callbacks(execute=True):
            _add_class(organization, document.id, "Pedido")
            _add_class(organization, document.id, "Cliente")
            _add_class(organization, document.id, "Factura")

        assert len(recorder) == 1

    def test_a_failing_push_never_breaks_saving_the_change(self, monkeypatch, django_capture_on_commit_callbacks):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        cache.clear()

        def boom(**_kwargs):
            raise RuntimeError("push is down")

        monkeypatch.setattr(service, "notify_organization", boom)

        with django_capture_on_commit_callbacks(execute=True):
            result = _add_class(organization, document.id, "Pedido")

        assert result.document.revision >= 1
