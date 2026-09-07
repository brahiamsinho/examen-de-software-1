"""Ninja/Pydantic request and response schemas for the organizations
domain. No ORM access here — `api.py` maps model instances onto these
shapes.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import Schema
from pydantic import EmailStr

from apps.organizations.constants import Plan, Role


class OrganizationIn(Schema):
    name: str
    slug: str
    plan: Plan = Plan.STARTER


class OrganizationPatchIn(Schema):
    name: str


class OrganizationOut(Schema):
    id: UUID
    name: str
    slug: str
    plan: str
    my_role: str | None


class MemberAddIn(Schema):
    email: EmailStr
    role: Literal["EDITOR", "VIEWER"]


class RoleChangeIn(Schema):
    role: Role


class MembershipOut(Schema):
    user_id: UUID
    email: str
    full_name: str
    role: str
    created_at: datetime
