"""Ninja/Pydantic request and response schemas for the ai_assistant domain,
mirroring `apps.uml_documents.schemas`'s convention (no ORM access here —
`api.py` maps `service.py`-shaped dataclasses onto these shapes).
"""
from ninja import Schema
from pydantic import Field, field_validator


class VoiceCommandIn(Schema):
    transcript: str


class AppliedCommandOut(Schema):
    ok: bool
    message: str


class VoiceCommandOut(Schema):
    revision: int
    applied: list[AppliedCommandOut]


class VoiceCommandPreviewOut(Schema):
    plan_id: str
    base_revision: int
    changes: list[AppliedCommandOut]


class VoiceCommandConfirmIn(Schema):
    plan_id: str


class ImageImportPreviewOut(Schema):
    plan_id: str
    base_revision: int
    changes: list[AppliedCommandOut]


class ImageImportConfirmIn(Schema):
    plan_id: str


class ProposalRequestIn(Schema):
    prompt: str = Field(max_length=2000)

    @field_validator("prompt")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tell the AI what you want ideas about.")
        return value


class ChatMessageIn(Schema):
    content: str = Field(max_length=2000)

    @field_validator("content")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Write a message first.")
        return value


class ChatMessageOut(Schema):
    id: int
    document_id: str
    author: str
    author_id: str | None
    is_ai: bool
    content: str
    created_at: str


class ApproveProposalIn(Schema):
    # Indices into the proposal's `changes`/`calls`; omitted or null applies all.
    selected: list[int] | None = None


class ProposalCallOut(Schema):
    name: str
    args: dict


class ProposalOut(Schema):
    id: str
    document_id: str
    status: str
    prompt: str
    base_revision: int
    changes: list[AppliedCommandOut]
    calls: list[ProposalCallOut]
    applied_indices: list[int] | None
    requested_by: str | None
    decided_by: str | None
    created_at: str
    decided_at: str | None


class ChatPostOut(Schema):
    message: ChatMessageOut
    reply: ChatMessageOut | None
    ai_error: str | None
    # The draft the AI left on the board when the message asked it to change something.
    proposal: ProposalOut | None
