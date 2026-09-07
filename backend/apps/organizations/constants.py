"""Shared choice enums for the organizations domain.

Kept out of `models.py` so `schemas.py` and `services.py` can import these
codes without importing the ORM graph.
"""
from django.db import models


class Role(models.TextChoices):
    OWNER = "OWNER", "Propietario"
    EDITOR = "EDITOR", "Editor"
    VIEWER = "VIEWER", "Lector"


class Plan(models.TextChoices):
    STARTER = "STARTER", "Starter"
    TEAM = "TEAM", "Team"
    ENTERPRISE = "ENTERPRISE", "Enterprise"
