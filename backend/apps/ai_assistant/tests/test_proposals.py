"""Service tests for AI board proposals (issue #15): the AI suggests changes
as drafts that never touch the document until a developer approves them."""
from unittest import mock

import pytest
from django.http import Http404
from django.utils import timezone

from apps.ai_assistant import proposals
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services


class _FakeClient:
    def __init__(self, calls):
        self._calls = calls
        self.transcripts: list[str] = []

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        self.transcripts.append(transcript)
        return self._calls


def _document(organization, owner):
    return services.create_document(
        organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now()
    )


def _add_class(organization, doc_id, name="Persona"):
    return services.submit_commands(
        organization=organization,
        doc_id=doc_id,
        commands_to_apply=[services.command_from_payload(_payload(name))],
        now=timezone.now(),
    )


def _payload(name):
    from apps.uml_documents import schemas

    return schemas.AddClassIn(type="AddClass", class_id=f"id-{name}", name=name)


def _suggest(organization, doc_id, user, calls=None, prompt="What is missing?"):
    calls = calls if calls is not None else [GeminiFunctionCall(name="add_class", args={"name": "Pedido"})]
    return proposals.create_proposal(
        organization=organization,
        doc_id=doc_id,
        requested_by=user,
        prompt=prompt,
        gemini=_FakeClient(calls),
    )


@pytest.mark.django_db
class TestCreateProposal:
    def test_the_proposal_is_a_pending_draft_and_the_document_is_untouched(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        proposal = _suggest(organization, document.id, owner)

        assert proposal.status == "pending"
        assert proposal.base_revision == document.revision
        assert proposal.requested_by == owner
        assert proposal.changes[0]["ok"] is True
        assert "Pedido" in proposal.changes[0]["message"]
        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision
        assert after.model.classes == ()

    def test_the_model_sees_the_diagram_and_the_request(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        client = _FakeClient([GeminiFunctionCall(name="add_class", args={"name": "Pedido"})])

        proposals.create_proposal(
            organization=organization, doc_id=document.id, requested_by=owner, prompt="Add orders", gemini=client
        )

        assert "Add orders" in client.transcripts[0]
        assert "empty" in client.transcripts[0]

    def test_an_answer_with_no_suggestions_is_rejected_with_a_clear_message(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with pytest.raises(proposals.NoSuggestionsError):
            _suggest(organization, document.id, owner, calls=[])

    def test_a_foreign_organization_cannot_propose_on_the_document(self):
        organization, owner, *_ = make_org_with_roles()
        other_organization, other_owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with pytest.raises(Http404):
            _suggest(other_organization, document.id, other_owner)


@pytest.mark.django_db
class TestDecideProposal:
    def test_approving_applies_the_changes_and_records_who_decided(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)

        approved = proposals.approve_proposal(
            organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
        )

        assert approved.status == "approved"
        assert approved.decided_by == editor
        assert approved.decided_at is not None
        after = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in after.model.classes] == ["Pedido"]
        assert after.revision == document.revision + 1

    def test_rejecting_leaves_the_document_unchanged(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)

        rejected = proposals.reject_proposal(
            organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
        )

        assert rejected.status == "rejected"
        assert rejected.decided_by == editor
        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision and after.model.classes == ()

    def test_a_proposal_goes_stale_when_the_diagram_changes_and_cannot_be_approved(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)
        _add_class(organization, document.id, "Persona")

        with pytest.raises(proposals.StaleProposalError):
            proposals.approve_proposal(
                organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
            )

        refreshed = proposals.get_proposal(organization=organization, doc_id=document.id, proposal_id=proposal.id)
        assert refreshed.status == "stale"
        after = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in after.model.classes] == ["Persona"]

    def test_a_decided_proposal_cannot_be_decided_again(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)
        proposals.reject_proposal(
            organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
        )

        with pytest.raises(proposals.ProposalAlreadyDecidedError):
            proposals.approve_proposal(
                organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
            )

    def test_a_proposal_with_unapplicable_changes_cannot_be_approved(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(
            organization,
            document.id,
            owner,
            calls=[GeminiFunctionCall(name="rename_class", args={"class_name": "Ghost", "new_name": "X"})],
        )

        assert proposal.changes[0]["ok"] is False
        with pytest.raises(proposals.UnapplicableProposalError):
            proposals.approve_proposal(
                organization=organization, doc_id=document.id, proposal_id=proposal.id, decided_by=editor, now=timezone.now()
            )
        assert (
            services.get_document(organization=organization, doc_id=document.id).revision == document.revision
        )

    def test_another_organization_cannot_read_or_decide_the_proposal(self):
        organization, owner, *_ = make_org_with_roles()
        other_organization, other_owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        proposal = _suggest(organization, document.id, owner)

        with pytest.raises(Http404):
            proposals.approve_proposal(
                organization=other_organization,
                doc_id=document.id,
                proposal_id=proposal.id,
                decided_by=other_owner,
                now=timezone.now(),
            )
        with pytest.raises(Http404):
            proposals.list_proposals(organization=other_organization, doc_id=document.id)


@pytest.mark.django_db
class TestListAndBroadcast:
    def test_lists_only_pending_proposals_and_marks_outdated_ones_stale(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        old = _suggest(organization, document.id, owner)
        _add_class(organization, document.id, "Persona")
        fresh = _suggest(organization, document.id, owner)
        rejected = _suggest(organization, document.id, owner)
        proposals.reject_proposal(
            organization=organization, doc_id=document.id, proposal_id=rejected.id, decided_by=editor, now=timezone.now()
        )

        listed = proposals.list_proposals(organization=organization, doc_id=document.id)

        assert [item.id for item in listed] == [fresh.id]
        assert proposals.get_proposal(organization=organization, doc_id=document.id, proposal_id=old.id).status == "stale"

    def test_creating_and_deciding_broadcast_the_proposal_to_the_document_group(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with mock.patch("apps.ai_assistant.proposals.services.broadcast_event") as broadcast:
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr("django.db.transaction.on_commit", lambda fn: fn())
                proposal = _suggest(organization, document.id, owner)
                proposals.reject_proposal(
                    organization=organization,
                    doc_id=document.id,
                    proposal_id=proposal.id,
                    decided_by=editor,
                    now=timezone.now(),
                )

        types = [call.kwargs["payload"]["type"] for call in broadcast.call_args_list]
        assert types == ["proposal.update", "proposal.update"]
        assert broadcast.call_args_list[-1].kwargs["payload"]["proposal"]["status"] == "rejected"
