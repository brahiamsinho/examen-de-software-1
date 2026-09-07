"""Invariant-bearing operations for the users domain.

HTTP-agnostic, keyword-only, raising `errors.py` exceptions. Transaction
boundaries live here, not in views, so a later Channels consumer or
management command can call these functions directly.
"""
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.organizations.services import create_organization, derive_workspace_name, generate_unique_slug
from apps.users.errors import DuplicateEmailError, InvalidCredentialsError, PasswordPolicyError
from apps.users.models import User


@transaction.atomic
def register_user(*, email: str, password: str, full_name: str = "") -> User:
    """Create a `User`, after validating the password against the project's
    configured password validators, and provision exactly one `Organization`
    with the new user as `OWNER` in the same transaction (user-authentication
    spec: "Registration Provisions One Organization"; design.md DD2). If
    organization provisioning fails, the whole transaction rolls back — no
    `User` row may persist without its organization.
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
        user = User.objects.create_user(email=email, password=password, full_name=full_name)
    except IntegrityError as exc:
        raise DuplicateEmailError(f"A user with email '{email}' already exists.") from exc

    source = full_name.strip() or normalized_email.split("@", 1)[0]
    create_organization(
        owner=user,
        name=derive_workspace_name(source=source),
        slug=generate_unique_slug(source=source),
    )
    return user


def authenticate_user(*, email: str, password: str) -> User:
    """Authenticate by email/password. Raises one generic error for both
    an unknown email and a wrong password (user-authentication spec: no
    email enumeration).
    """
    user = authenticate(username=email, password=password)
    if user is None:
        raise InvalidCredentialsError("Invalid email or password.")
    return user
