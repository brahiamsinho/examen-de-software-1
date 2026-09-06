"""Ninja/Pydantic request and response schemas for the users domain.
No ORM access here — `api.py` maps model instances onto these shapes.
"""
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


class CsrfOut(Schema):
    csrf_token: str
