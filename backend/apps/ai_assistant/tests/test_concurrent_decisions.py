"""Two people deciding the same AI proposal at the same moment, on MongoDB.

Exactly one decision may win. The loser's transaction is aborted by MongoDB
(write conflict) and re-run by `config.transactions`; on the re-run it finds the
proposal already decided and is refused, as it would be a second later.
"""

import threading
from unittest import mock

import pytest
from django.db import connection
from django.utils import timezone

from apps.ai_assistant import proposals
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.ai_assistant.tests.test_proposals import _FakeClient, _document
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services


@pytest.mark.django_db(transaction=True)
def test_approving_and_rejecting_at_once_lets_exactly_one_decision_win():
    organization, owner, editor, *_ = make_org_with_roles()
    document = _document(organization, owner)
    proposal = proposals.create_proposal(
        organization=organization,
        doc_id=document.id,
        requested_by=owner,
        prompt="What is missing?",
        gemini=_FakeClient([GeminiFunctionCall(name="add_class", args={"name": "Pedido"})]),
    )

    # Keep whoever reaches the log write waiting for the other. If both were
    # allowed in, both decisions would be recorded; the loser times out of the
    # barrier only because it never gets this far.
    barrier = threading.Barrier(2)
    real_record = proposals.session_log.record

    def meeting_point(*args, **kwargs):
        try:
            barrier.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        return real_record(*args, **kwargs)

    outcomes: dict[str, str] = {}

    def decide(label: str, action) -> None:
        try:
            action(
                organization=organization,
                doc_id=document.id,
                proposal_id=proposal.id,
                decided_by=editor,
                now=timezone.now(),
            )
            outcomes[label] = "decided"
        except proposals.ProposalAlreadyDecidedError:
            outcomes[label] = "refused"
        finally:
            connection.close()

    with mock.patch.object(proposals.session_log, "record", side_effect=meeting_point):
        threads = [
            threading.Thread(target=decide, args=("approve", proposals.approve_proposal)),
            threading.Thread(target=decide, args=("reject", proposals.reject_proposal)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

    assert sorted(outcomes.values()) == ["decided", "refused"]
    final = proposals.get_proposal(organization=organization, doc_id=document.id, proposal_id=proposal.id)
    assert final.status in {"approved", "rejected"}
    revision = services.get_document(organization=organization, doc_id=document.id).revision
    # An approval applies the change (one revision up); a rejection leaves the diagram alone.
    assert revision == document.revision + (1 if final.status == "approved" else 0)
