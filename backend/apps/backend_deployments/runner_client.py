"""HTTP client for the `runner` service (stdlib only: no new dependency).

The only place Django talks to the runner. Tests inject a fake with the same
three methods; nothing in this app imports Docker.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol

from django.conf import settings


class RunnerError(Exception):
    """Base class for every runner failure."""


class RunnerUnavailableError(RunnerError):
    """The runner could not be reached (down, misconfigured, timeout)."""


class RunnerRejectedError(RunnerError):
    """The runner answered with an error status (e.g. it rejected the archive)."""


class RunnerClientProtocol(Protocol):
    def start(self, deployment_id: str, org_slug: str, archive: bytes) -> dict: ...
    def status(self, deployment_id: str) -> dict | None: ...
    def stop(self, deployment_id: str) -> None: ...


class RunnerClient:
    def __init__(self, base_url: str, token: str, timeout: float):
        self._base = base_url.rstrip("/")
        self._token = token
        self._timeout = timeout

    def _call(self, method: str, path: str, body: bytes | None = None, content_type: str | None = None):
        if not self._token:
            raise RunnerUnavailableError("RUNNER_TOKEN is not configured.")
        request = urllib.request.Request(f"{self._base}{path}", data=body, method=method)
        request.add_header("Authorization", f"Bearer {self._token}")
        if content_type:
            request.add_header("Content-Type", content_type)
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                raw = response.read()
                return response.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = json.loads(exc.read()).get("detail", "")
            except (ValueError, AttributeError):
                pass
            return exc.code, {"detail": detail or f"runner answered {exc.code}"}
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RunnerUnavailableError("The deployment runner is unreachable.") from exc

    def start(self, deployment_id: str, org_slug: str, archive: bytes) -> dict:
        query = urllib.parse.urlencode({"org": org_slug})
        code, payload = self._call(
            "PUT", f"/deployments/{deployment_id}?{query}", archive, "application/zip"
        )
        if code != 202:
            raise RunnerRejectedError(payload.get("detail", f"runner answered {code}"))
        return payload

    def status(self, deployment_id: str) -> dict | None:
        code, payload = self._call("GET", f"/deployments/{deployment_id}")
        if code == 404:
            return None
        if code != 200:
            raise RunnerRejectedError(payload.get("detail", f"runner answered {code}"))
        return payload

    def stop(self, deployment_id: str) -> None:
        code, payload = self._call("DELETE", f"/deployments/{deployment_id}")
        if code not in (204, 404):
            raise RunnerRejectedError(payload.get("detail", f"runner answered {code}"))


def get_runner_client() -> RunnerClientProtocol:
    return RunnerClient(settings.RUNNER_URL, settings.RUNNER_TOKEN, settings.RUNNER_TIMEOUT_SECONDS)
