"""User model contract: custom email-identified user, Argon2 hashing,
case-insensitive email uniqueness enforced at both the manager layer and
the database layer (DD7 in design.md).
"""
import pytest
from django.db import IntegrityError
from django.db import transaction

from apps.identity.models import User


@pytest.mark.django_db
def test_email_uniqueness_is_case_insensitive_via_manager():
    User.objects.create_user(email="alice@example.com", password="a-strong-pass-1")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(email="Alice@Example.com", password="another-pass-2")


@pytest.mark.django_db
def test_email_uniqueness_enforced_by_functional_index_even_bypassing_manager():
    """Even a writer that bypasses `UserManager.normalize_email` (raw
    `.create()`) must still be rejected by the DB-level `Lower(email)`
    unique constraint, not just application-level normalization.
    """
    User.objects.create(email="bob@example.com", password="irrelevant-hash")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(email="Bob@EXAMPLE.com", password="irrelevant-hash-2")


@pytest.mark.django_db
def test_password_is_stored_as_argon2_hash():
    user = User.objects.create_user(email="carol@example.com", password="a-strong-pass-3")

    assert user.password.startswith("argon2$")
    assert user.password != "a-strong-pass-3"


def test_username_field_is_email_and_no_username_field():
    assert User.USERNAME_FIELD == "email"
    assert User.REQUIRED_FIELDS == []
    field_names = {f.name for f in User._meta.get_fields()}
    assert "username" not in field_names
    assert "email" in field_names


@pytest.mark.django_db
def test_create_superuser_sets_staff_and_superuser_flags():
    admin = User.objects.create_superuser(email="admin@example.com", password="a-strong-pass-4")

    assert admin.is_staff is True
    assert admin.is_superuser is True
