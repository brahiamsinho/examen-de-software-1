"""Service-layer tests for `register_user` / `authenticate_user`.

Called directly, without HTTP, per design.md's Testing Strategy — so a
later Channels consumer or management command is covered by the same
tests.
"""
import pytest

from apps.organizations.constants import Role
from apps.organizations.errors import OrganizationError
from apps.organizations.models import Membership, Organization
from apps.users import services
from apps.users.errors import DuplicateEmailError, InvalidCredentialsError, PasswordPolicyError
from apps.users.models import User
from apps.users.tests.factories import make_user


@pytest.mark.django_db
class TestRegisterUser:
    def test_creates_user_with_hashed_password(self):
        user = services.register_user(
            email="new@example.com", password="a-very-strong-pass-1", full_name="New User"
        )

        assert isinstance(user, User)
        assert user.email == "new@example.com"
        assert user.full_name == "New User"
        assert user.password != "a-very-strong-pass-1"
        assert user.check_password("a-very-strong-pass-1")

    def test_duplicate_email_rejected(self):
        make_user(email="taken@example.com")

        with pytest.raises(DuplicateEmailError):
            services.register_user(email="taken@example.com", password="a-very-strong-pass-1")

    def test_duplicate_email_rejected_case_insensitive(self):
        make_user(email="taken@example.com")

        with pytest.raises(DuplicateEmailError):
            services.register_user(email="Taken@Example.com", password="a-very-strong-pass-1")

    def test_weak_password_rejected(self):
        with pytest.raises(PasswordPolicyError):
            services.register_user(email="weak@example.com", password="123")

        assert not User.objects.filter(email="weak@example.com").exists()

    def test_registration_provisions_exactly_one_organization_with_owner_membership(self):
        user = services.register_user(
            email="workspace@example.com", password="a-very-strong-pass-1", full_name="Work Space"
        )

        organizations = Organization.objects.filter(memberships__user=user)
        assert organizations.count() == 1
        membership = Membership.all_objects.get(organization=organizations.first(), user=user)
        assert membership.role == Role.OWNER

    def test_organization_provisioning_failure_rolls_back_the_user(self, monkeypatch):
        def _raise_organization_error(*, source):
            raise OrganizationError("Could not generate a unique organization slug.")

        monkeypatch.setattr(services, "generate_unique_slug", _raise_organization_error)

        with pytest.raises(OrganizationError):
            services.register_user(
                email="rollback@example.com", password="a-very-strong-pass-1", full_name="Roll Back"
            )

        assert User.objects.count() == 0


@pytest.mark.django_db
class TestAuthenticateUser:
    def test_valid_credentials_returns_user(self):
        user = make_user(email="valid@example.com", password="a-very-strong-pass-1")

        result = services.authenticate_user(email="valid@example.com", password="a-very-strong-pass-1")

        assert result.pk == user.pk

    def test_wrong_password_rejected_generically(self):
        make_user(email="valid2@example.com", password="a-very-strong-pass-1")

        with pytest.raises(InvalidCredentialsError):
            services.authenticate_user(email="valid2@example.com", password="wrong-password")

    def test_unknown_email_rejected_generically(self):
        with pytest.raises(InvalidCredentialsError):
            services.authenticate_user(email="nobody@example.com", password="a-very-strong-pass-1")
