"""Tests for `apps/users/emails.py` (transactional-email spec § "Plain-Text
Message Dispatch"; design.md's header-injection threat-matrix row).
"""
import pytest
from django.core import mail

from apps.users.emails import send_reset_email, send_verification_email
from apps.users.tests.factories import make_user


@pytest.mark.django_db
def test_verification_email_is_plain_text_only():
    user = make_user(email="alice@example.com")

    send_verification_email(user=user, raw_token="raw-token-value")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.content_subtype == "plain"
    assert not message.alternatives
    assert "raw-token-value" in message.body


@pytest.mark.django_db
def test_reset_email_is_plain_text_only():
    user = make_user(email="bob@example.com")

    send_reset_email(user=user, raw_token="another-raw-token")

    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.content_subtype == "plain"
    assert not message.alternatives
    assert "another-raw-token" in message.body


@pytest.mark.django_db
def test_verification_email_recipient_is_always_the_db_email_not_a_spoofed_value():
    """Header-injection case (design.md threat matrix): even if a caller
    somehow influenced a "recipient-looking" string, the function itself
    takes no recipient argument — it always reads `user.email` from the DB.
    """
    user = make_user(email="real-owner@example.com")

    send_verification_email(user=user, raw_token="tok")

    assert mail.outbox[0].to == ["real-owner@example.com"]


@pytest.mark.django_db
def test_reset_email_recipient_is_always_the_db_email():
    user = make_user(email="real-owner-2@example.com")

    send_reset_email(user=user, raw_token="tok2")

    assert mail.outbox[0].to == ["real-owner-2@example.com"]
