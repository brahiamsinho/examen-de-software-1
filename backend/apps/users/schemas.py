"""Ninja/Pydantic request and response schemas for the users domain.
No ORM access here — `api.py` maps model instances onto these shapes.
"""
from datetime import datetime
from ninja import Schema
from pydantic import EmailStr
from uuid import UUID


class RegisterIn(Schema):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginIn(Schema):
    email: EmailStr
    password: str


class UserOut(Schema):
    id: UUID
    email: str
    full_name: str
    is_verified: bool


class CsrfOut(Schema):
    csrf_token: str


class MobileLoginIn(LoginIn):
    # Free text shown nowhere yet; it lets a user tell their devices apart.
    device_name: str = ""


class MobileTokenOut(Schema):
    token: str
    expires_at: datetime
    user: UserOut


class VerifyIn(Schema):
    token: str


class ResetRequestIn(Schema):
    email: EmailStr


class ResetConfirmIn(Schema):
    token: str
    password: str


class MessageOut(Schema):
    message: str
