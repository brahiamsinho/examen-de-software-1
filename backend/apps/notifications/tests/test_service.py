"""Sending pushes: only to organization members, retried, never breaking the caller."""
import pytest

from apps.notifications import fcm, service
from apps.notifications.models import DeviceToken
from apps.organizations.tests.factories import make_org_with_roles


@pytest.fixture(autouse=True)
def configured_and_synchronous(monkeypatch):
    monkeypatch.setattr(fcm, "is_configured", lambda: True)
    monkeypatch.setattr(service, "_run_in_background", lambda job: job())
    monkeypatch.setattr(service.time, "sleep", lambda _seconds: None)


class _Sender:
    """Records every send and answers per call from `outcomes`."""

    def __init__(self, outcomes=None):
        self.sent = []
        self._outcomes = list(outcomes or [])

    def __call__(self, tokens, *, title, body, data):
        self.sent.append({"tokens": sorted(tokens), "title": title, "body": body, "data": data})
        return self._outcomes.pop(0) if self._outcomes else fcm.SendResult()


def _device(user, token):
    return DeviceToken.objects.create(user=user, token=token, platform="android")


@pytest.mark.django_db
class TestFanOut:
    def test_only_members_of_the_organization_are_notified(self, monkeypatch):
        organization, owner, editor, viewer, outsider = make_org_with_roles()
        for user, token in [(owner, "t-owner"), (editor, "t-editor"), (viewer, "t-viewer"), (outsider, "t-outsider")]:
            _device(user, token)
        sender = _Sender()
        monkeypatch.setattr(fcm, "send", sender)

        service.notify_organization(
            organization_id=organization.id, title="T", body="B", data={"type": "proposal"}
        )

        assert sender.sent[0]["tokens"] == ["t-editor", "t-owner", "t-viewer"]
        assert sender.sent[0]["data"] == {"type": "proposal"}

    def test_the_person_who_caused_the_event_is_left_out(self, monkeypatch):
        organization, owner, editor, *_ = make_org_with_roles()
        _device(owner, "t-owner")
        _device(editor, "t-editor")
        sender = _Sender()
        monkeypatch.setattr(fcm, "send", sender)

        service.notify_organization(
            organization_id=organization.id, title="T", body="B", data={}, exclude_user_id=owner.id
        )

        assert sender.sent[0]["tokens"] == ["t-editor"]

    def test_nothing_is_sent_when_nobody_has_a_device(self, monkeypatch):
        organization, *_ = make_org_with_roles()
        sender = _Sender()
        monkeypatch.setattr(fcm, "send", sender)

        service.notify_organization(organization_id=organization.id, title="T", body="B", data={})

        assert sender.sent == []

    def test_nothing_is_sent_when_firebase_is_not_configured(self, monkeypatch):
        organization, owner, *_ = make_org_with_roles()
        _device(owner, "t-owner")
        sender = _Sender()
        monkeypatch.setattr(fcm, "send", sender)
        monkeypatch.setattr(fcm, "is_configured", lambda: False)

        service.notify_organization(organization_id=organization.id, title="T", body="B", data={})

        assert sender.sent == []


@pytest.mark.django_db
class TestUnreliableDelivery:
    def test_tokens_firebase_says_are_dead_are_deleted(self, monkeypatch):
        organization, owner, editor, *_ = make_org_with_roles()
        _device(owner, "alive")
        _device(editor, "dead")
        monkeypatch.setattr(fcm, "send", _Sender([fcm.SendResult(invalid=["dead"])]))

        service.notify_organization(organization_id=organization.id, title="T", body="B", data={})

        assert list(DeviceToken.objects.values_list("token", flat=True)) == ["alive"]

    def test_a_transient_failure_is_retried_only_for_the_tokens_that_failed(self, monkeypatch):
        organization, owner, editor, *_ = make_org_with_roles()
        _device(owner, "ok")
        _device(editor, "flaky")
        sender = _Sender([fcm.SendResult(retry=["flaky"]), fcm.SendResult()])
        monkeypatch.setattr(fcm, "send", sender)

        service.notify_organization(organization_id=organization.id, title="T", body="B", data={})

        assert [call["tokens"] for call in sender.sent] == [["flaky", "ok"], ["flaky"]]

    def test_retrying_stops_after_a_few_attempts(self, monkeypatch):
        organization, owner, *_ = make_org_with_roles()
        _device(owner, "flaky")
        sender = _Sender([fcm.SendResult(retry=["flaky"])] * 10)
        monkeypatch.setattr(fcm, "send", sender)

        service.notify_organization(organization_id=organization.id, title="T", body="B", data={})

        assert len(sender.sent) == service.MAX_ATTEMPTS

    def test_a_crashing_sender_never_reaches_the_caller(self, monkeypatch):
        organization, owner, *_ = make_org_with_roles()
        _device(owner, "t")

        def boom(*args, **kwargs):
            raise RuntimeError("firebase is down")

        monkeypatch.setattr(fcm, "send", boom)

        service.notify_organization(organization_id=organization.id, title="T", body="B", data={})
