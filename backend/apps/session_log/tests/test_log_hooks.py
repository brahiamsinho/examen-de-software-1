"""What gets recorded, by whom, when something happens in a diagram (issue #17):
changes (by people, by voice, by approving an AI proposal), proposal decisions
and chat messages. Each hook runs in the same transaction as its action."""
from unittest import mock

import pytest
from django.utils import timezone

from apps.ai_assistant import chat, proposals
from apps.ai_assistant import service as ai_service
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.organizations.tests.factories import make_org_with_roles
from apps.session_log.models import LogEntry
from apps.uml_documents import schemas, services


def _document(organization, owner):
    return services.create_document(organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now())


def _entries(organization, document):
    return list(LogEntry.objects.for_organization(organization).filter(document_id=document.id).order_by("id"))


def _label(user):
    return user.full_name or user.email


def _add_class(name):
    return services.command_from_payload(schemas.AddClassIn(type="AddClass", class_id=f"id-{name}", name=name))


class _Model:
    def __init__(self, calls):
        self._calls = calls

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        return self._calls


def _suggest(*names):
    return _Model(
        [
            GeminiFunctionCall(
                name="suggest_uml_additions",
                args={"classes": [{"name": name, "attributes": [], "operations": []} for name in names], "relationships": []},
            )
        ]
    )


@pytest.mark.django_db
class TestChangesAreRecorded:
    def test_a_command_sent_over_http_is_recorded_with_its_author_and_what_it_did(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{document.id}/commands",
            data={"type": "AddClass", "class_id": "c1", "name": "Pedido"},
            content_type="application/json",
        )

        assert response.status_code == 200
        (entry,) = _entries(organization, document)
        assert entry.kind == "change" and entry.actor_id == editor.id and entry.actor_label == _label(editor)
        assert entry.summary == "AddClass Pedido"
        assert entry.data["commands"] == [{"type": "AddClass", "label": "Pedido"}]
        assert entry.data["revision"] == response.json()["revision"]

    def test_a_batch_is_one_entry_that_lists_every_command(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        services.submit_commands(
            organization=organization,
            doc_id=document.id,
            commands_to_apply=[_add_class("A"), _add_class("B"), _add_class("C")],
            now=timezone.now(),
            actor=editor,
        )

        (entry,) = _entries(organization, document)
        assert entry.data["total"] == 3 and entry.summary == "AddClass A; AddClass B; AddClass C"

    def test_a_change_without_a_known_author_is_still_recorded_as_the_system(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        services.submit_commands(
            organization=organization, doc_id=document.id, commands_to_apply=[_add_class("A")], now=timezone.now()
        )

        (entry,) = _entries(organization, document)
        assert entry.actor_label == "Sistema" and entry.actor_id is None

    def test_a_change_that_is_refused_leaves_no_entry(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with pytest.raises(ValueError):
            services.submit_commands(
                organization=organization,
                doc_id=document.id,
                commands_to_apply=[_add_class("A")],
                now=timezone.now(),
                expected_revision=document.revision + 5,
                actor=editor,
            )

        assert _entries(organization, document) == []

    def test_restoring_a_version_is_recorded(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        version = services.create_version(
            organization=organization,
            doc_id=document.id,
            created_by=owner,
            description="v1",
            expected_revision=document.revision,
        )
        changed = services.submit_commands(
            organization=organization, doc_id=document.id, commands_to_apply=[_add_class("A")], now=timezone.now(), actor=owner
        )

        services.restore_version(
            organization=organization,
            doc_id=document.id,
            version_id=version.id,
            expected_revision=changed.document.revision,
            now=timezone.now(),
            actor=editor,
        )

        entry = _entries(organization, document)[-1]
        assert entry.kind == "version.restored" and entry.actor_id == editor.id
        assert entry.data["version_id"] == str(version.id) and entry.data["version_number"] == version.number

    def test_replacing_the_diagram_with_an_import_is_recorded(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        services.replace_document_content(
            organization=organization,
            doc_id=document.id,
            model=document.model,
            layout=document.layout,
            now=timezone.now(),
            actor=editor,
        )

        (entry,) = _entries(organization, document)
        assert entry.kind == "diagram.replaced" and entry.actor_id == editor.id

    def test_a_confirmed_voice_command_is_recorded_for_the_person_who_confirmed_it(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        model = _Model([GeminiFunctionCall(name="add_class", args={"name": "Pedido"})])
        preview = ai_service.preview_voice_command(
            organization=organization, doc_id=document.id, transcript="agrega pedido", gemini=model
        )

        ai_service.confirm_voice_command(
            organization=organization, doc_id=document.id, plan_id=preview.plan_id, now=timezone.now(), actor=editor
        )

        (entry,) = _entries(organization, document)
        assert entry.kind == "change" and entry.actor_id == editor.id and "AddClass" in entry.summary


@pytest.mark.django_db
class TestAiProposalsAreRecorded:
    def _propose(self, organization, document, requested_by, names=("Rol",)):
        return proposals.create_proposal(
            organization=organization,
            doc_id=document.id,
            requested_by=requested_by,
            prompt="agrega roles",
            gemini=_suggest(*names),
        )

    def _decide(self, organization, document, proposal, user, approve=True, selected=None):
        call = proposals.approve_proposal if approve else proposals.reject_proposal
        extra = {"selected": selected} if approve else {}
        return call(
            organization=organization,
            doc_id=document.id,
            proposal_id=proposal.id,
            decided_by=user,
            now=timezone.now(),
            **extra,
        )

    def test_what_the_ai_proposed_is_recorded_as_the_ai_with_who_asked_for_it(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        proposal = self._propose(organization, document, editor)

        (entry,) = _entries(organization, document)
        assert entry.kind == "proposal.created" and entry.is_ai is True and entry.actor_label == "IA"
        assert entry.data["proposal_id"] == str(proposal.id)
        assert entry.data["requested_by"] == _label(editor)
        assert entry.data["prompt"] == "agrega roles"
        assert entry.data["changes"] == [change["message"] for change in proposal.changes]

    def test_approving_records_the_change_and_the_decision_for_the_approver(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = self._propose(organization, document, editor, names=("Rol", "Permiso"))

        self._decide(organization, document, proposal, owner, selected=[0])

        created, change, decision = _entries(organization, document)
        assert [created.kind, change.kind, decision.kind] == ["proposal.created", "change", "proposal.approved"]
        assert change.actor_id == owner.id and change.summary == "AddClass Rol"
        assert decision.actor_id == owner.id and decision.is_ai is False
        assert decision.data == {"proposal_id": str(proposal.id), "applied_indices": [0], "total_changes": 2}
        assert decision.summary == "Approved AI proposal (1 of 2 changes)"

    def test_rejecting_records_who_rejected_it_and_changes_nothing_else(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = self._propose(organization, document, editor)

        self._decide(organization, document, proposal, owner, approve=False)

        kinds = [entry.kind for entry in _entries(organization, document)]
        assert kinds == ["proposal.created", "proposal.rejected"]
        assert _entries(organization, document)[-1].actor_id == owner.id

    def test_a_refused_approval_records_nothing(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = self._propose(organization, document, editor)

        with pytest.raises(proposals.InvalidSelectionError):
            self._decide(organization, document, proposal, owner, selected=[])

        assert [entry.kind for entry in _entries(organization, document)] == ["proposal.created"]

    def test_a_proposal_left_from_the_chat_is_recorded_like_any_other(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        model = _Model(
            [
                GeminiFunctionCall(name="reply_in_chat", args={"message": "Dejé un borrador."}),
                *_suggest("Rol")._calls,
            ]
        )

        chat.post_message(organization=organization, doc_id=document.id, author=editor, content="@IA agrega Rol", gemini=model)

        kinds = [entry.kind for entry in _entries(organization, document)]
        assert kinds == ["chat.message", "proposal.created", "chat.message"]


@pytest.mark.django_db
class TestChatMessagesAreRecorded:
    def test_a_message_is_recorded_with_its_author_and_text(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        result = chat.post_message(
            organization=organization, doc_id=document.id, author=editor, content="Yo hago Cliente", gemini=_Model([])
        )

        (entry,) = _entries(organization, document)
        assert entry.kind == "chat.message" and entry.actor_id == editor.id
        assert entry.summary == "Yo hago Cliente" and entry.data == {"message_id": str(result.message.id)}

    def test_the_ais_reply_is_recorded_as_the_ai(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        model = _Model([GeminiFunctionCall(name="reply_in_chat", args={"message": "Hola equipo"})])

        chat.post_message(organization=organization, doc_id=document.id, author=editor, content="@IA hola", gemini=model)

        human, ai = _entries(organization, document)
        assert (human.is_ai, ai.is_ai) == (False, True)
        assert ai.summary == "Hola equipo" and ai.actor_label == "IA"

    def test_a_long_message_is_cut_in_the_log_but_not_in_the_chat(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        result = chat.post_message(
            organization=organization, doc_id=document.id, author=editor, content="x" * 1500, gemini=_Model([])
        )

        (entry,) = _entries(organization, document)
        assert len(entry.summary) == 500 and len(result.message.content) == 1500

    def test_everything_in_one_sitting_shares_one_session(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        chat.post_message(organization=organization, doc_id=document.id, author=editor, content="hola", gemini=_Model([]))
        services.submit_commands(
            organization=organization, doc_id=document.id, commands_to_apply=[_add_class("A")], now=timezone.now(), actor=owner
        )

        assert {entry.session for entry in _entries(organization, document)} == {1}
