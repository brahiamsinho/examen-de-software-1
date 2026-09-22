"""Ninja/Pydantic request and response schemas for the ai_assistant domain,
mirroring `apps.uml_documents.schemas`'s convention (no ORM access here —
`api.py` maps `service.py`-shaped dataclasses onto these shapes).
"""
from ninja import Schema


class VoiceCommandIn(Schema):
    transcript: str


class AppliedCommandOut(Schema):
    ok: bool
    message: str


class VoiceCommandOut(Schema):
    revision: int
    applied: list[AppliedCommandOut]
