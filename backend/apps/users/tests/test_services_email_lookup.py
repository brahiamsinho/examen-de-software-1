"""Email lookups on MongoDB must match the address, not a pattern.

`django-mongodb-backend` implements `__iexact` as an unescaped regular
expression, so the `.` in "john.smith@example.com" matched any character and
found "johnxsmith@example.com". Emails are stored lowercased, so lookups use an
exact match on the lowercased value instead.
"""

import pytest
from django.core import mail

from apps.organizations import services as org_services
from apps.organizations.constants import Role
from apps.organizations.tests.factories import make_org_with_roles
from apps.users import services
from apps.users.errors import DuplicateEmailError, UserNotFoundError
from apps.users.models import User

PASSWORD = "a-very-strong-pass-1"
LOOKALIKE = "johnxsmith@example.com"
DOTTED = "john.smith@example.com"


@pytest.mark.django_db
def test_a_dot_in_the_email_is_not_a_wildcard_when_registering():
    services.register_user(email=LOOKALIKE, password=PASSWORD)

    user = services.register_user(email=DOTTED, password=PASSWORD)

    assert user.email == DOTTED
    with pytest.raises(DuplicateEmailError):
        services.register_user(email="JOHN.SMITH@example.com", password=PASSWORD)


@pytest.mark.django_db
def test_adding_a_member_never_picks_a_lookalike_address():
    organization, *_ = make_org_with_roles()
    services.register_user(email=LOOKALIKE, password=PASSWORD)

    with pytest.raises(UserNotFoundError):
        org_services.add_member(organization=organization, email=DOTTED, role=Role.EDITOR)


@pytest.mark.django_db
def test_adding_a_member_matches_the_address_whatever_its_letter_case():
    organization, *_ = make_org_with_roles()
    user = services.register_user(email=DOTTED, password=PASSWORD)

    membership = org_services.add_member(organization=organization, email="John.Smith@Example.COM", role=Role.EDITOR)

    assert membership.user_id == user.id


@pytest.mark.django_db
def test_a_password_reset_for_a_dotted_address_never_reaches_a_lookalike_account(monkeypatch):
    monkeypatch.setattr(services, "_RESET_ANTI_ENUMERATION_DELAY_SECONDS", 0)
    services.register_user(email=LOOKALIKE, password=PASSWORD)
    mail.outbox.clear()

    services.request_password_reset(email=DOTTED)

    assert [message.to for message in mail.outbox] == []
    assert User.objects.filter(email=LOOKALIKE).exists()
