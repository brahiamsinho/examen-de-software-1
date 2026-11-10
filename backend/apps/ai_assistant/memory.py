"""Semantic memory of the team chat.

Every chat message is turned into a vector of its *meaning* by an embedding model
(a transformer encoder, so deep learning). When someone asks `@IA`, the question is
embedded too and the closest earlier messages are shown to the model: from other
diagrams of the same organization, or from further back in this one. That is how the
AI can recall what the team said before without a longer and longer chat window.

Boundaries that matter:
- Only the caller's organization is ever searched (`for_organization`).
- A vector is only compared with vectors made by the same embedding model.
- It is best-effort: a provider without embeddings, or one that fails, just means
  no memory. The chat itself never depends on it.
"""
import logging
import math
import re
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.conf import settings
from django.db import connections

from apps.ai_assistant.models import ChatMessage
from apps.organizations.models import Organization
from apps.uml_documents import services

logger = logging.getLogger(__name__)

MEMORY_RESULTS = 4
# Brute force over the latest messages is plenty for a team chat and needs no vector database.
MAX_CANDIDATES = 500
MAX_TEXT_LENGTH = 2000
AI_LABEL = "IA"

_HEADER = (
    "Earlier team conversation that may be relevant (from other diagrams or further back in this one). "
    "Use it only if it truly helps the current question, and say which diagram it came from:"
)


@dataclass(frozen=True)
class Memory:
    content: str
    author: str
    diagram: str
    created_at: datetime
    score: float


# `@IA` is how someone calls the AI, not what the message is about. Left in, every
# "@IA que..." would look alike and drag in unrelated conversations.
_MENTION = re.compile(r"(?<![\w@])@ia(?!\w)", re.IGNORECASE)


def _text_to_embed(content: str) -> str:
    return " ".join(_MENTION.sub(" ", content).split())[:MAX_TEXT_LENGTH]


def _run_in_background(job: Callable[[], None]) -> None:
    def target() -> None:
        try:
            job()
        finally:
            connections.close_all()  # a thread owns its own database connection

    threading.Thread(target=target, daemon=True).start()


def _embedder(client):
    """The client if it can embed, else `None` (Gemini, or a test double)."""
    return client if callable(getattr(client, "embed", None)) else None


def remember(organization: Organization, messages: Iterable[ChatMessage], client) -> None:
    """Stores the vectors of `messages` without making the writer wait. Never raises."""
    embedder = _embedder(client)
    items = [(message.id, _text_to_embed(message.content)) for message in messages]
    items = [(message_id, text) for message_id, text in items if text]
    if embedder is None or not items:
        return
    organization_id = organization.id

    def job() -> None:
        try:
            vectors = embedder.embed([text for _, text in items])
            for (message_id, _), vector in zip(items, vectors, strict=True):
                ChatMessage.all_objects.filter(pk=message_id, organization_id=organization_id).update(
                    embedding=vector, embedding_model=embedder.embedding_model
                )
        except Exception:  # noqa: BLE001 - memory is a courtesy; see module docstring
            logger.warning("Could not remember a chat message", exc_info=True)

    _run_in_background(job)


class EmbeddingsUnavailable(RuntimeError):
    """The active provider cannot make embeddings (e.g. Gemini here)."""


def backfill(client, *, batch_size: int = 50) -> int:
    """Gives a vector to every message written before the memory existed (or while the
    provider was down). Returns how many it did. Unlike the chat, this reports problems:
    it is run by a person who wants to know."""
    embedder = _embedder(client)
    if embedder is None:
        raise EmbeddingsUnavailable("The active AI provider does not support embeddings.")
    done = 0
    while True:
        batch = list(
            ChatMessage.all_objects.filter(embedding_model="").exclude(content="").order_by("id")[:batch_size]
        )
        if not batch:
            return done
        vectors = embedder.embed([_text_to_embed(item.content) or item.content[:MAX_TEXT_LENGTH] for item in batch])
        for item, vector in zip(batch, vectors, strict=True):
            ChatMessage.all_objects.filter(pk=item.id).update(embedding=vector, embedding_model=embedder.embedding_model)
        done += len(batch)


def _cosine(a: list[float], b: list[float], norm_b: float) -> float:
    norm_a = math.sqrt(sum(value * value for value in a))
    if norm_a == 0 or norm_b == 0 or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b, strict=True)) / (norm_a * norm_b)


def _author_label(message: ChatMessage) -> str:
    if message.is_ai:
        return AI_LABEL
    if message.author is None:
        return "Former member"
    return message.author.full_name or message.author.email


def _diagram_name(organization: Organization, doc_id: UUID, current: UUID) -> str:
    if doc_id == current:
        return "this diagram (earlier)"
    try:
        return services.get_document(organization=organization, doc_id=doc_id).metadata.name or "another diagram"
    except Exception:  # noqa: BLE001 - a deleted diagram should not hide what was said in it
        return "another diagram"


def recall(
    *, organization: Organization, doc_id: UUID, question: str, already_shown: set, client
) -> list[Memory]:
    """The earlier messages closest in meaning to `question`, best first. Never raises."""
    embedder = _embedder(client)
    text = _text_to_embed(question or "")
    if embedder is None or not text:
        return []
    try:
        [query] = embedder.embed([text])
        model_name = embedder.embedding_model
        candidates = (
            ChatMessage.objects.for_organization(organization)
            .filter(embedding_model=model_name)
            .exclude(id__in=already_shown)
            .select_related("author")
            .order_by("-id")[:MAX_CANDIDATES]
        )
        norm = math.sqrt(sum(value * value for value in query))
        scored = [
            (_cosine(item.embedding, query, norm), item)
            for item in candidates
            if isinstance(item.embedding, list)
        ]
        threshold = settings.CHAT_MEMORY_MIN_SIMILARITY
        best = sorted((pair for pair in scored if pair[0] >= threshold), key=lambda pair: -pair[0])[:MEMORY_RESULTS]
        return [
            Memory(
                content=item.content,
                author=_author_label(item),
                diagram=_diagram_name(organization, item.document_id, doc_id),
                created_at=item.created_at,
                score=score,
            )
            for score, item in best
        ]
    except Exception:  # noqa: BLE001 - memory is a courtesy; see module docstring
        logger.warning("Could not recall earlier conversation", exc_info=True)
        return []


def render(memories: list[Memory]) -> str:
    """The block added to what the model reads; empty when there is nothing to recall."""
    if not memories:
        return ""
    lines = "\n".join(
        f'- In "{item.diagram}", {item.author} said ({item.created_at:%Y-%m-%d}): {item.content}' for item in memories
    )
    return f"{_HEADER}\n{lines}"
