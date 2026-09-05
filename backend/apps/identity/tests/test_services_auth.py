"""Service-layer tests for `register_user` / `authenticate_user`.

Called directly, without HTTP, per design.md's Testing Strategy — so a
later Channels consumer or management command is covered by the same
tests.
"""
import pytest

from apps.identity import services
from apps.identity.errors import DuplicateEmailError, InvalidCredentialsError, PasswordPolicyError
from apps.identity.models import User
from apps.identity.tests.factories import make_user


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
