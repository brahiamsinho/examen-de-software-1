import pytest
from django.test import Client

from apps.backend_deployments import service
from apps.backend_deployments.runner_client import RunnerUnavailableError


class FakeRunner:
    """Same three methods as `RunnerClient`; records calls, never touches a network."""

    def __init__(self):
        self.started: list[tuple[str, str, bytes]] = []
        self.stopped: list[str] = []
        self.states: dict[str, dict | None] = {}
        self.down = False

    def _check(self):
        if self.down:
            raise RunnerUnavailableError("The deployment runner is unreachable.")

    def start(self, deployment_id, org_slug, archive):
        self._check()
        self.started.append((deployment_id, org_slug, archive))
        return {"status": "queued"}

    def status(self, deployment_id):
        self._check()
        return self.states.get(deployment_id)

    def stop(self, deployment_id):
        self._check()
        self.stopped.append(deployment_id)


@pytest.fixture
def fake_runner(monkeypatch) -> FakeRunner:
    runner = FakeRunner()
    monkeypatch.setattr(service, "get_runner_client", lambda: runner)
    return runner


@pytest.fixture
def auth_client() -> Client:
    return Client()
