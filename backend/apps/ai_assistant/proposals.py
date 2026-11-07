"""AI board proposals (issue #15): the AI acts as one more developer.

A teammate asks the AI for an idea; the answer is stored as a pending
`AiProposal` and broadcast to everyone on the document. Nothing changes in the
diagram until an OWNER/EDITOR approves it, and a proposal that was written for
an older revision goes stale instead of being applied blindly.

Reuses the voice/image machinery: the same tools, `Translator`, and
`services.submit_commands`, so an approved proposal is applied exactly like any
other command batch.
"""
import datetime
from uuid import UUID

from django.db import transaction
from django.http import Http404

from apps.ai_assistant import service, tools
from apps.ai_assistant.gemini_client import GeminiClientProtocol, GeminiFunctionCall
from apps.ai_assistant.llm_provider import get_active_llm_client
from apps.ai_assistant.models import AiProposal, ProposalStatus
from apps.ai_assistant.translator import Translator
from apps.organizations.models import Organization
from apps.uml_documents import services

_PROPOSAL_INSTRUCTION = (
    "You are a teammate on a UML class diagram editor, working alongside human "
    "developers. A developer asks for your ideas about the diagram. Answer ONLY "
    "with the provided function calls, one call per distinct improvement, in a "
    "sensible order. Propose concrete, useful changes (missing classes, "
    "attributes, relationships). Never repeat something that already exists in "
    "the diagram and never invent changes that do not follow from the request. "
    "Refer to classes and attributes by name, never by id. If nothing useful can "
    "be added, make no calls."
)


class ProposalError(ValueError):
    """Base for every proposal refusal. `api.py` maps a `ValueError` to HTTP 409."""


class NoSuggestionsError(ProposalError):
    def __init__(self) -> None:
        super().__init__("The AI had no suggestions for this diagram right now. Try asking in a different way.")


class StaleProposalError(ProposalError):
    def __init__(self) -> None:
        super().__init__("The diagram changed after this proposal was made. Ask the AI again.")


class ProposalAlreadyDecidedError(ProposalError):
    def __init__(self, status: str) -> None:
        super().__init__(f"This proposal was already {status}.")


class UnapplicableProposalError(ProposalError):
    def __init__(self) -> None:
        super().__init__("This proposal contains changes that cannot be applied. Reject it and ask the AI again.")


def _label(user) -> str | None:
    if user is None:
        return None
    return user.full_name or user.email


def serialize_proposal(proposal: AiProposal) -> dict:
    """JSON-safe shape shared by the HTTP API and the WebSocket event."""
    return {
        "id": str(proposal.id),
        "document_id": str(proposal.document_id),
        "status": proposal.status,
        "prompt": proposal.prompt,
        "base_revision": proposal.base_revision,
        "changes": proposal.changes,
        "calls": proposal.calls,
        "requested_by": _label(proposal.requested_by),
        "decided_by": _label(proposal.decided_by),
        "created_at": proposal.created_at.isoformat(),
        "decided_at": proposal.decided_at.isoformat() if proposal.decided_at else None,
    }


def _broadcast(proposal: AiProposal) -> None:
    payload = {"type": "proposal.update", "proposal": serialize_proposal(proposal)}
    document_id = proposal.document_id
    transaction.on_commit(lambda: services.broadcast_event(document_id=document_id, payload=payload))


def _rows(organization: Organization, doc_id: UUID):
    # `get_document` is the single org+document existence check (404 when the
    # document is foreign or missing), so a proposal can never be reached
    # through another organization's slug.
    document = services.get_document(organization=organization, doc_id=doc_id)
    return document, AiProposal.objects.for_organization(organization).filter(document_id=doc_id)


def _mark_stale_if_outdated(proposal: AiProposal, revision: int) -> AiProposal:
    if proposal.status == ProposalStatus.PENDING and proposal.base_revision != revision:
        proposal.status = ProposalStatus.STALE
        proposal.save(update_fields=["status"])
        _broadcast(proposal)
    return proposal


def create_proposal(
    *,
    organization: Organization,
    doc_id: UUID,
    requested_by,
    prompt: str,
    gemini: GeminiClientProtocol | None = None,
) -> AiProposal:
    """Ask the model for ideas and store them as a pending draft. Never writes
    to the document. Raises `NoSuggestionsError` when the model has nothing."""
    gemini = gemini or get_active_llm_client()
    document = services.get_document(organization=organization, doc_id=doc_id)
    calls = gemini.generate_function_calls(
        system_instruction=_PROPOSAL_INSTRUCTION,
        transcript=f"{service.document_context(document)}\n\nA teammate asked: {prompt}",
        tools=tools.TOOLS,
    )
    if not calls:
        raise NoSuggestionsError()

    changes = [
        {"ok": item.ok, "message": item.message} for item in service.describe_calls(document, calls)
    ]
    with transaction.atomic():
        proposal = AiProposal.objects.for_organization(organization).create(
            organization=organization,
            document_id=doc_id,
            prompt=prompt,
            base_revision=document.revision,
            calls=[{"name": call.name, "args": dict(call.args)} for call in calls],
            changes=changes,
            requested_by=requested_by,
        )
        _broadcast(proposal)
    return proposal


def get_proposal(*, organization: Organization, doc_id: UUID, proposal_id: UUID) -> AiProposal:
    document, queryset = _rows(organization, doc_id)
    proposal = queryset.filter(id=proposal_id).select_related("requested_by", "decided_by").first()
    if proposal is None:
        raise Http404("Proposal not found")
    return _mark_stale_if_outdated(proposal, document.revision)


def list_proposals(*, organization: Organization, doc_id: UUID) -> list[AiProposal]:
    """Pending proposals for the document; outdated ones are marked stale first."""
    document, queryset = _rows(organization, doc_id)
    pending = list(
        queryset.filter(status=ProposalStatus.PENDING).select_related("requested_by", "decided_by")
    )
    return [
        proposal
        for proposal in (_mark_stale_if_outdated(item, document.revision) for item in pending)
        if proposal.status == ProposalStatus.PENDING
    ]


def _decidable(proposal: AiProposal) -> None:
    if proposal.status == ProposalStatus.STALE:
        raise StaleProposalError()
    if proposal.status != ProposalStatus.PENDING:
        raise ProposalAlreadyDecidedError(proposal.get_status_display().lower())


def approve_proposal(
    *,
    organization: Organization,
    doc_id: UUID,
    proposal_id: UUID,
    decided_by,
    now: datetime.datetime,
) -> AiProposal:
    """Apply the proposal's changes as one command batch, then mark it approved."""
    # Staleness is checked (and persisted) outside the atomic block below, so
    # the `stale` mark survives the refusal that follows it.
    proposal = get_proposal(organization=organization, doc_id=doc_id, proposal_id=proposal_id)
    _decidable(proposal)
    if not proposal.changes or any(not change["ok"] for change in proposal.changes):
        raise UnapplicableProposalError()

    with transaction.atomic():
        locked = (
            AiProposal.objects.for_organization(organization)
            .select_for_update(of=("self",))
            .select_related("requested_by", "decided_by")
            .get(id=proposal_id)
        )
        _decidable(locked)
        document = services.get_document(organization=organization, doc_id=doc_id)
        translator = Translator(document.model)
        translated = [
            translator.translate(GeminiFunctionCall(name=call["name"], args=call["args"]))
            for call in locked.calls
        ]
        services.submit_commands(
            organization=organization,
            doc_id=doc_id,
            commands_to_apply=[services.command_from_payload(item.payload) for item in translated],
            now=now,
            expected_revision=locked.base_revision,
        )
        locked.status = ProposalStatus.APPROVED
        locked.decided_by = decided_by
        locked.decided_at = now
        locked.save(update_fields=["status", "decided_by", "decided_at"])
        _broadcast(locked)
    return locked


def reject_proposal(
    *,
    organization: Organization,
    doc_id: UUID,
    proposal_id: UUID,
    decided_by,
    now: datetime.datetime,
) -> AiProposal:
    proposal = get_proposal(organization=organization, doc_id=doc_id, proposal_id=proposal_id)
    _decidable(proposal)
    with transaction.atomic():
        locked = (
            AiProposal.objects.for_organization(organization)
            .select_for_update(of=("self",))
            .select_related("requested_by", "decided_by")
            .get(id=proposal_id)
        )
        _decidable(locked)
        locked.status = ProposalStatus.REJECTED
        locked.decided_by = decided_by
        locked.decided_at = now
        locked.save(update_fields=["status", "decided_by", "decided_at"])
        _broadcast(locked)
    return locked
