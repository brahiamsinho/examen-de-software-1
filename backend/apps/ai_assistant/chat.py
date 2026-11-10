"""Group chat per diagram with one AI model (issue #16).

Developers talk to each other in a chat tied to the diagram. A message that
mentions `@IA` also wakes the model, which receives the recent conversation of
EVERYONE (each line carries its author) and answers as one more participant.
Messages that do not mention it are only stored and shown, so the team can talk
without spending tokens.

Every message is its own database row ordered by its auto id and broadcast on
the document socket, so two people writing at once never lose or mix messages.
The chat never changes the diagram itself: when the model wants to change
something it leaves a draft proposal on the board (the same kind as "Pide
ideas a la IA") that a developer approves.
"""
import re
from dataclasses import dataclass
from uuid import UUID

from django_mongodb_backend import transaction

from apps.ai_assistant import proposals, service, tools
from apps.ai_assistant.errors import GeminiRequestError, MissingApiKeyError
from apps.ai_assistant.gemini_client import GeminiClientProtocol, GeminiFunctionCall
from apps.ai_assistant.llm_provider import get_active_llm_client
from apps.ai_assistant.models import AiProposal, ChatMessage
from apps.organizations.models import Organization
from apps.session_log import services as session_log
from apps.uml_documents import services

# Bounds the tokens (and so the cost) of one model call: only the latest
# messages are sent, and no single message can be huge.
CONTEXT_MESSAGES = 30
MAX_MESSAGE_LENGTH = 2000
HISTORY_LIMIT = 100
AI_LABEL = "IA"

# `@IA` as its own word: not part of an email (`a@ia.com`) nor of `@IAmigos`.
_MENTION = re.compile(r"(?<![\w@])@ia(?!\w)", re.IGNORECASE)

_CHAT_INSTRUCTION = (
    "You are 'IA', one more teammate in a group chat of developers who are building "
    "a UML class diagram together. Each chat line is 'Author: text'. Several people "
    "talk; keep their contributions apart and answer the most recent message that "
    "mentions @IA, using what the others said earlier when it matters. Reply in the "
    "language of the conversation, briefly, by calling reply_in_chat once. You never "
    "edit the diagram directly. When the team asks you to add or change something, call "
    "suggest_uml_additions with a COMPLETE suggestion (each new class with its attributes "
    "and operations, and its relationships): it leaves a draft on the board that a "
    "developer approves. Then say in reply_in_chat that you left a draft for them to "
    "approve; never say you already added or changed anything. If you have nothing "
    "useful to add, make no call. " + tools.RELATIONSHIP_GUIDANCE
)

# Said by the chat itself when the model left a draft but wrote no sentence.
_DRAFT_NOTICE = "Dejé una propuesta en la pizarra para que el equipo la revise y la apruebe."


class ChatError(ValueError):
    """Base for chat refusals."""


class InvalidMessageError(ChatError):
    pass


@dataclass(frozen=True)
class ChatResult:
    message: ChatMessage
    reply: ChatMessage | None = None
    ai_error: str | None = None
    # The draft the AI left on the board when it was asked to change something.
    proposal: AiProposal | None = None


def mentions_ai(content: str) -> bool:
    return _MENTION.search(content) is not None


def _label(user) -> str:
    if user is None:
        return "Former member"
    return user.full_name or user.email


def serialize_message(message: ChatMessage) -> dict:
    """JSON-safe shape shared by the HTTP API and the WebSocket event."""
    return {
        "id": str(message.id),
        "document_id": str(message.document_id),
        "author": AI_LABEL if message.is_ai else _label(message.author),
        "author_id": str(message.author_id) if message.author_id else None,
        "is_ai": message.is_ai,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


def _broadcast(message: ChatMessage) -> None:
    payload = {"type": "chat.message", "message": serialize_message(message)}
    document_id = message.document_id
    transaction.on_commit(lambda: services.broadcast_event(document_id=document_id, payload=payload))


def _store(organization: Organization, doc_id: UUID, *, author, content: str, is_ai: bool) -> ChatMessage:
    with transaction.atomic():
        message = ChatMessage.objects.for_organization(organization).create(
            organization=organization, document_id=doc_id, author=author, is_ai=is_ai, content=content
        )
        session_log.record(
            organization=organization,
            document_id=doc_id,
            kind=session_log.LogKind.CHAT_MESSAGE,
            summary=content,
            actor=author,
            is_ai=is_ai,
            data={"message_id": str(message.id)},
            now=message.created_at,
        )
        _broadcast(message)
    return message


def list_messages(*, organization: Organization, doc_id: UUID, limit: int = HISTORY_LIMIT) -> list[ChatMessage]:
    """The latest `limit` messages, oldest first. `get_document` is the single
    org+document check (404 for a foreign or missing document), so a chat can
    never be reached through another organization's slug."""
    services.get_document(organization=organization, doc_id=doc_id)
    latest = (
        ChatMessage.objects.for_organization(organization)
        .filter(document_id=doc_id)
        .select_related("author")
        .order_by("-id")[:limit]
    )
    return list(reversed(list(latest)))


def _transcript(document, history: list[ChatMessage]) -> str:
    lines = "\n".join(f"{AI_LABEL if item.is_ai else _label(item.author)}: {item.content}" for item in history)
    return f"{service.document_context(document)}\n\nGroup chat, oldest first:\n{lines}"


def _ask_model(
    organization: Organization, doc_id: UUID, gemini: GeminiClientProtocol | None
) -> tuple[str | None, list[GeminiFunctionCall]]:
    """Returns the model's chat sentence (if any) and the changes it wants to make."""
    gemini = gemini or get_active_llm_client()
    document = services.get_document(organization=organization, doc_id=doc_id)
    history = list_messages(organization=organization, doc_id=doc_id, limit=CONTEXT_MESSAGES)
    calls = gemini.generate_function_calls(
        system_instruction=_CHAT_INSTRUCTION,
        transcript=_transcript(document, history),
        tools=tools.CHAT_TOOLS + tools.PROPOSAL_TOOLS,
    )
    sentence = None
    suggestions = []
    for call in calls:
        if call.name == "reply_in_chat" and sentence is None:
            text = str(call.args.get("message", "")).strip()
            sentence = text[:MAX_MESSAGE_LENGTH] if text else None
        elif call.name == "suggest_uml_additions":
            suggestions.append(call)
    return sentence, suggestions


def post_message(
    *,
    organization: Organization,
    doc_id: UUID,
    author,
    content: str,
    gemini: GeminiClientProtocol | None = None,
) -> ChatResult:
    """Stores the human's message (it is kept even if the model fails) and, when
    it mentions `@IA`, stores the model's answer as a second message."""
    text = (content or "").strip()
    if not text:
        raise InvalidMessageError("Write a message first.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise InvalidMessageError(f"A message can have at most {MAX_MESSAGE_LENGTH} characters.")
    services.get_document(organization=organization, doc_id=doc_id)

    message = _store(organization, doc_id, author=author, content=text, is_ai=False)
    if not mentions_ai(text):
        return ChatResult(message=message)

    try:
        sentence, suggestions = _ask_model(organization, doc_id, gemini)
    except GeminiRequestError:
        return ChatResult(message=message, ai_error="The AI did not answer in time. Mention it again to retry.")
    except MissingApiKeyError:
        return ChatResult(message=message, ai_error="The AI is not configured for this workspace.")

    # Changes become a draft on the board (the diagram only changes once a
    # developer approves it), attributed to whoever asked.
    proposal = None
    if suggestions:
        document = services.get_document(organization=organization, doc_id=doc_id)
        proposal = proposals.propose_calls(
            organization=organization, document=document, requested_by=author, prompt=text, calls=suggestions
        )
    if proposal is not None and sentence is None:
        sentence = _DRAFT_NOTICE
    if sentence is None:
        return ChatResult(message=message, proposal=proposal)
    reply = _store(organization, doc_id, author=None, content=sentence, is_ai=True)
    return ChatResult(message=message, reply=reply, proposal=proposal)
