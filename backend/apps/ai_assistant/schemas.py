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
    requested_by: str | None
    decided_by: str | None
    created_at: str
    decided_at: str | None
