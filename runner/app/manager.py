"""Deployment lifecycle: queued -> building -> starting -> running | failed | stopped.

State is in memory only. That is deliberate: on start the runner sweeps every
labelled container/network/volume (`DockerOps.cleanup_all`), so a restart can
never leave a deployment the runner does not know about. Django treats a 404
from `GET /deployments/{id}` as "lost" and marks the row stopped.
"""
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

from .archive import InvalidArchiveError, zip_to_tar
from .config import Settings
from .docker_ops import DockerOps, container_name

ACTIVE = ("queued", "building", "starting", "running")


class DeploymentExists(Exception):
    pass


@dataclass
class Deployment:
    id: str
    org: str
    status: str = "queued"
    error: str = ""
    events: list[str] = field(default_factory=list)
    password: str = field(default_factory=lambda: secrets.token_urlsafe(24), repr=False)
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None


class DeploymentManager:
    def __init__(
        self,
        ops: DockerOps,
        settings: Settings,
        *,
        probe: Callable[[str, int], bool],
        sleep: Callable[[float], None] = time.sleep,
        executor: ThreadPoolExecutor | None = None,
    ):
        self._ops = ops
        self._s = settings
        self._probe = probe  # (container name, port) -> True once /v3/api-docs answers 200
        self._sleep = sleep
        self._executor = executor or ThreadPoolExecutor(max_workers=settings.max_workers)
        self._deployments: dict[str, Deployment] = {}
        self._lock = threading.Lock()

    # ---- public API -------------------------------------------------------------

    def submit(self, dep_id: str, org: str, zip_bytes: bytes) -> Deployment:
        # Validate synchronously so a bad archive is a 4xx, not a failed deployment.
        tar_bytes = zip_to_tar(
            zip_bytes,
            max_zip_bytes=self._s.max_zip_bytes,
            max_unpacked_bytes=self._s.max_unpacked_bytes,
            max_files=self._s.max_zip_files,
        )
        with self._lock:
            if dep_id in self._deployments:
                raise DeploymentExists(dep_id)
            deployment = Deployment(id=dep_id, org=org)
            self._deployments[dep_id] = deployment
        self._executor.submit(self._run, deployment, tar_bytes)
        return deployment

    def get(self, dep_id: str) -> Deployment | None:
        return self._deployments.get(dep_id)

    def public_view(self, deployment: Deployment) -> dict:
        base = f"{self._s.public_base_url}/gen/{deployment.id}/"
        logs = deployment.events[-self._s.log_tail_lines :]
        if deployment.status in ("starting", "running"):
            live = self._ops.logs_tail(container_name(deployment.id, "app"))
            logs = logs + live.splitlines()[-self._s.log_tail_lines :]
        text = "\n".join(logs).replace(deployment.password, "***")
        return {
            "id": deployment.id,
            "status": deployment.status,
            "error": deployment.error,
            "log_tail": text[-8000:],
            "public_path": f"/gen/{deployment.id}/",
            "public_url": base,
            "openapi_url": f"{base}v3/api-docs",
        }

    def stop(self, dep_id: str) -> None:
        """Idempotent: removes whatever is labelled with this id, known or not."""
        self._ops.remove_deployment(dep_id)
        deployment = self._deployments.get(dep_id)
        if deployment and deployment.status != "stopped":
            deployment.status = "stopped"
            deployment.finished_at = time.time()

    def startup_cleanup(self) -> None:
        self._ops.cleanup_all()

    def reap_expired(self) -> list[str]:
        now = time.time()
        reaped = []
        for deployment in list(self._deployments.values()):
            if deployment.status in ACTIVE and now - deployment.created_at > self._s.max_lifetime:
                self.stop(deployment.id)
                deployment.events.append("[runner] lifetime exceeded: deployment removed")
                reaped.append(deployment.id)
            elif deployment.status == "stopped" and now - (deployment.finished_at or now) > 3600:
                self._deployments.pop(deployment.id, None)
        return reaped

    def run_reaper(self, stop_event: threading.Event) -> None:
        while not stop_event.wait(self._s.reaper_interval):
            try:
                self.reap_expired()
            except Exception:  # the reaper must never die
                pass

    # ---- pipeline (worker thread) -------------------------------------------------

    def _log(self, deployment: Deployment, line: str) -> None:
        deployment.events.append(f"[runner] {line}")

    def _fail(self, deployment: Deployment, message: str, logs: str = "") -> None:
        deployment.status = "failed"
        deployment.error = message
        deployment.finished_at = time.time()
        if logs:
            deployment.events.extend(logs.splitlines()[-self._s.log_tail_lines :])
        self._log(deployment, f"failed: {message}")
        self._ops.remove_deployment(deployment.id)  # never leave half-built resources

    def _run(self, deployment: Deployment, tar_bytes: bytes) -> None:
        dep_id, org = deployment.id, deployment.org
        try:
            deployment.status = "building"
            self._log(deployment, "building the project with Gradle")
            network = self._ops.create_network(dep_id, org)
            exit_code, logs = self._ops.run_build(dep_id, org, tar_bytes)
            if deployment.status == "stopped":  # deleted while building: sweep what we made
                return self._ops.remove_deployment(dep_id)
            if exit_code != 0:
                return self._fail(deployment, f"build failed (exit code {exit_code})", logs)

            deployment.status = "starting"
            self._log(deployment, "starting PostgreSQL")
            self._ops.start_db(dep_id, org, network, deployment.password)
            if not self._ops.wait_db_healthy(dep_id):
                return self._fail(deployment, "database did not become healthy")

            self._log(deployment, "starting the generated application")
            app_name = self._ops.start_app(dep_id, org, network, deployment.password)
            deadline = time.monotonic() + self._s.start_timeout
            while time.monotonic() < deadline:
                if deployment.status == "stopped":
                    return self._ops.remove_deployment(dep_id)
                if self._ops.app_state(dep_id) != "running":
                    logs = self._ops.logs_tail(app_name)
                    return self._fail(deployment, "the application exited during startup", logs)
                if self._probe(app_name, self._s.app_port):
                    deployment.status = "running"
                    self._log(deployment, "application is running")
                    return
                self._sleep(2)
            self._fail(deployment, "the application did not become ready in time",
                       self._ops.logs_tail(app_name))
        except InvalidArchiveError as exc:  # defensive; validated in submit()
            self._fail(deployment, str(exc))
        except Exception as exc:
            self._fail(deployment, f"runner error: {type(exc).__name__}")
