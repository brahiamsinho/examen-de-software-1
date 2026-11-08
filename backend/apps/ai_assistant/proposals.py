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
from collections.abc import Sequence
from uuid import UUID

from django.db import transaction
from django.http import Http404

from apps.ai_assistant import service, tools
from apps.ai_assistant.errors import TranslationError
from apps.ai_assistant.gemini_client import GeminiClientProtocol, GeminiFunctionCall
from apps.ai_assistant.llm_provider import get_active_llm_client
from apps.ai_assistant.models import AiProposal, ProposalStatus
from apps.ai_assistant.translator import Translator
from apps.organizations.models import Organization
from apps.session_log import services as session_log
from apps.uml_documents import services

_PROPOSAL_INSTRUCTION = (
    "You are a teammate on a UML class diagram editor, working alongside human "
    "developers. A developer asks for your ideas about the diagram. Answer ONLY "
    "by calling suggest_uml_additions once with a COMPLETE suggestion: every new "
    "class together with its attributes (name and type) and its operations, and "
    "every relationship between classes with its multiplicities. A class without "
    "attributes is rarely useful, so always include the fields it needs. You may "
    "list an existing class to give it new attributes or operations. Never repeat "
    "something that already exists in the diagram and never invent changes that "
    "do not follow from the request. Refer to classes by name, never by id. If "
    "nothing useful can be added, return empty lists. " + tools.RELATIONSHIP_GUIDANCE
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


class InvalidSelectionError(ProposalError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)


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
        "applied_indices": proposal.applied_indices,
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


def _key(value: object) -> str:
    return str(value).strip().casefold()


def _additions_only(document, calls: list[GeminiFunctionCall]) -> list[GeminiFunctionCall]:
    """Expands the structured suggestion into ordered UML commands and drops
    anything the diagram (or an earlier call) already has, so a proposal never
    proposes a duplicate class, attribute, operation or relationship. Calls the
    expander does not know (a plain `add_class`, `rename_class`...) pass through."""
    renamed = [
        GeminiFunctionCall(name="extract_uml_diagram", args=call.args)
        if call.name == "suggest_uml_additions"
        else call
        for call in calls
    ]
    expanded = service.expand_extraction(renamed)

    classes = {_key(item.name): item for item in document.model.classes}
    new_classes: set[str] = set()
    seen_members: set[tuple[str, str, str]] = set()
    seen_relationships: set[tuple[str, str, str]] = set()
    kept: list[GeminiFunctionCall] = []

    for call in expanded:
        args = call.args
        if call.name == "add_class":
            key = _key(args.get("name", ""))
            if key in classes or key in new_classes:
                continue
            new_classes.add(key)
        elif call.name in {"add_attribute", "add_operation"}:
            is_attribute = call.name == "add_attribute"
            class_key = _key(args.get("class_name", ""))
            member = _key(args.get("attribute_name" if is_attribute else "operation_name", ""))
            marker = (class_key, "a" if is_attribute else "o", member)
            existing = classes.get(class_key)
            already = existing is not None and member in {
                _key(item.name) for item in (existing.attributes if is_attribute else existing.operations)
            }
            if already or marker in seen_members:
                continue
            seen_members.add(marker)
        elif call.name == "add_relationship":
            source_key, target_key = _key(args.get("source_class_name", "")), _key(args.get("target_class_name", ""))
            marker = (str(args.get("kind", "")), source_key, target_key)
            source, target = classes.get(source_key), classes.get(target_key)
            already = (
                source is not None
                and target is not None
                and any(
                    item.kind.value == marker[0]
                    and item.source.class_id == source.id
                    and item.target.class_id == target.id
                    for item in document.model.relationships
                )
            )
            if already or marker in seen_relationships:
                continue
            seen_relationships.add(marker)
        kept.append(call)
    return kept


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
        tools=tools.PROPOSAL_TOOLS,
    )
    proposal = propose_calls(
        organization=organization, document=document, requested_by=requested_by, prompt=prompt, calls=list(calls)
    )
    if proposal is None:
        raise NoSuggestionsError()
    return proposal


def _with_multiplicities(call: GeminiFunctionCall, message: str) -> str:
    """Shows an approver what a relationship would really get, with the same
    defaults the translator applies, and flags a both-ends-many link: the editor
    derives its intermediate table, so approving it adds more than two classes
    and a line."""
    if call.name != "add_relationship":
        return message
    source = str(call.args.get("source_multiplicity") or "0..1")
    target = str(call.args.get("target_multiplicity") or "0..*")
    note = f" ({source} to {target}"
    if "*" in source and "*" in target:
        note += ", many-to-many: an intermediate table is derived from it"
    return f"{message}{note})"


def propose_calls(
    *,
    organization: Organization,
    document,
    requested_by,
    prompt: str,
    calls: list[GeminiFunctionCall],
) -> AiProposal | None:
    """Stores what the model wants to change as a pending draft and broadcasts
    it. Anything the diagram already has is dropped first; when nothing is left
    no draft is made (`None`). Never writes to the document. Shared by the
    "Pide ideas" panel and by the chat, so both create the same kind of draft."""
    calls = _additions_only(document, calls)
    if not calls:
        return None
    changes = [
        {"ok": item.ok, "message": _with_multiplicities(call, item.message)}
        for call, item in zip(calls, service.describe_calls(document, calls), strict=True)
    ]
    with transaction.atomic():
        proposal = AiProposal.objects.for_organization(organization).create(
            organization=organization,
            document_id=document.id,
            prompt=prompt,
            base_revision=document.revision,
            calls=[{"name": call.name, "args": dict(call.args)} for call in calls],
            changes=changes,
            requested_by=requested_by,
        )
        session_log.record(
            organization=organization,
            document_id=document.id,
            kind=session_log.LogKind.PROPOSAL_CREATED,
            summary=f"AI proposed {len(calls)} changes",
            is_ai=True,
            data={
                "proposal_id": str(proposal.id),
                "requested_by": _label(requested_by),
                "prompt": prompt[:500],
                "changes": [change["message"] for change in changes][:50],
            },
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


def _normalize_selection(selected: Sequence[int] | None, total: int) -> list[int]:
    """Sorted, de-duplicated indices; `None` means every change. Refuses an
    empty selection and any index outside the proposal."""
    if selected is None:
        return list(range(total))
    if not selected:
        raise InvalidSelectionError("Select at least one change to apply.")
    if any(isinstance(item, bool) or not isinstance(item, int) or not 0 <= item < total for item in selected):
        raise InvalidSelectionError("The selection refers to a change that is not in this proposal.")
    return sorted(set(selected))


def approve_proposal(
    *,
    organization: Organization,
    doc_id: UUID,
    proposal_id: UUID,
    decided_by,
    now: datetime.datetime,
    selected: Sequence[int] | None = None,
) -> AiProposal:
    """Apply the chosen changes of the proposal as one command batch, then mark
    it approved. `selected` holds indices into the proposal's changes; `None`
    applies all of them. The unchosen changes are discarded with the proposal.
    A selection that drops something a chosen change needs (an attribute
    without its class) is refused and nothing is written."""
    # Staleness is checked (and persisted) outside the atomic block below, so
    # the `stale` mark survives the refusal that follows it.
    proposal = get_proposal(organization=organization, doc_id=doc_id, proposal_id=proposal_id)
    _decidable(proposal)
    indices = _normalize_selection(selected, len(proposal.calls))
    if not indices or any(not proposal.changes[index]["ok"] for index in indices):
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
        try:
            translated = [
                translator.translate(
                    GeminiFunctionCall(name=locked.calls[index]["name"], args=locked.calls[index]["args"])
                )
                for index in indices
            ]
        except (TranslationError, KeyError, ValueError, TypeError) as exc:
            raise InvalidSelectionError(
                "The selected changes depend on changes that were not selected. "
                "Select the class an attribute or relationship belongs to."
            ) from exc
        services.submit_commands(
            organization=organization,
            doc_id=doc_id,
            commands_to_apply=[services.command_from_payload(item.payload) for item in translated],
            now=now,
            expected_revision=locked.base_revision,
            actor=decided_by,
        )
        locked.status = ProposalStatus.APPROVED
        locked.applied_indices = indices
        locked.decided_by = decided_by
        locked.decided_at = now
        locked.save(update_fields=["status", "applied_indices", "decided_by", "decided_at"])
        session_log.record(
            organization=organization,
            document_id=doc_id,
            kind=session_log.LogKind.PROPOSAL_APPROVED,
            summary=f"Approved AI proposal ({len(indices)} of {len(locked.calls)} changes)",
            actor=decided_by,
            data={
                "proposal_id": str(locked.id),
                "applied_indices": indices,
                "total_changes": len(locked.calls),
            },
            now=now,
        )
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
        session_log.record(
            organization=organization,
            document_id=doc_id,
            kind=session_log.LogKind.PROPOSAL_REJECTED,
            summary=f"Rejected AI proposal ({len(locked.calls)} changes)",
            actor=decided_by,
            data={"proposal_id": str(locked.id), "total_changes": len(locked.calls)},
            now=now,
        )
        _broadcast(locked)
    return locked
