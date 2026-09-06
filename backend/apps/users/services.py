"""Invariant-bearing operations for the users domain.

HTTP-agnostic, keyword-only, raising `errors.py` exceptions. Transaction
boundaries live here, not in views, so a later Channels consumer or
management command can call these functions directly.
"""
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.users.errors import DuplicateEmailError, InvalidCredentialsError, PasswordPolicyError
from apps.users.models import User


def register_user(*, email: str, password: str, full_name: str = "") -> User:
    """Create a `User` after validating the password against the
    project's configured password validators (user-authentication spec).
    """
    from django.contrib.auth.password_validation import validate_password

    normalized_email = User.objects.normalize_email(email)
    if User.objects.filter(email__iexact=normalized_email).exists():
        raise DuplicateEmailError(f"A user with email '{email}' already exists.")

    try:
        validate_password(password)
    except ValidationError as exc:
        raise PasswordPolicyError("; ".join(exc.messages)) from exc

    try:
        return User.objects.create_user(email=email, password=password, full_name=full_name)
    except IntegrityError as exc:
        raise DuplicateEmailError(f"A user with email '{email}' already exists.") from exc


def authenticate_user(*, email: str, password: str) -> User:
    """Authenticate by email/password. Raises one generic error for both
    an unknown email and a wrong password (user-authentication spec: no
    email enumeration).
    """
    user = authenticate(username=email, password=password)
    if user is None:
        raise InvalidCredentialsError("Invalid email or password.")
    return user
