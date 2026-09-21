"""The ONLY module that talks to the Docker Engine.

Every container is created through `_create`, which enforces the security
contract in one place: image from the fixed allowlist, no privileged mode, no
host network, no capabilities, no new privileges, memory/CPU/pids limits, and
only NAMED volumes (never a host path). Nothing here accepts an image, a
command or a mount source from a request: callers pass a deployment id (UUID)
and an organization slug (validated upstream), and the commands are constants.
"""
import re
import socket
import time
from typing import Callable

from .config import Settings

MANAGED_LABEL = "modelia.managed"
DEPLOYMENT_LABEL = "modelia.deployment"
ORG_LABEL = "modelia.org"
_NAME_RE = re.compile(r"^modelia-[a-z0-9-]+$")

WORKSPACE_DIR = "/workspace"
GRADLE_CACHE_DIR = "/gradle-cache"
JAR_PATH = f"{WORKSPACE_DIR}/app.jar"
# Constant build script: never assembled from request data. `bootJar` yields the
# executable jar (no `-plain` twin); it is copied to a fixed name for the app.
BUILD_COMMAND = [
    "sh",
    "-c",
    "gradle bootJar --no-daemon --console=plain "
    '&& for f in build/libs/*.jar; do case "$f" in *-plain.jar) ;; *) cp "$f" '
    + JAR_PATH
    + " ;; esac; done && test -f "
    + JAR_PATH,
]


class ImageNotAllowedError(RuntimeError):
    pass


def network_name(dep_id: str) -> str:
    return f"modelia-dep-{dep_id}"


def container_name(dep_id: str, role: str) -> str:
    return f"modelia-dep-{dep_id}-{role}"


def workspace_volume(dep_id: str) -> str:
    return f"modelia-dep-{dep_id}-ws"


def db_volume(dep_id: str) -> str:
    return f"modelia-dep-{dep_id}-pg"


class DockerOps:
    def __init__(self, client, settings: Settings, *, sleep: Callable[[float], None] = time.sleep):
        self._client = client
        self._s = settings
        self._sleep = sleep

    # ---- security choke point -------------------------------------------------

    def _create(
        self,
        *,
        image: str,
        name: str,
        dep_id: str,
        org: str,
        mem: str,
        cpus: float,
        volumes: dict[str, dict],
        network: str | None = None,
        **extra,
    ):
        if image not in self._s.images:
            raise ImageNotAllowedError(f"image not in allowlist: {image}")
        for volume_name in volumes:
            if not _NAME_RE.match(volume_name):  # named volumes only, never a host path
                raise ImageNotAllowedError(f"volume source must be a runner-owned name: {volume_name}")
        self.ensure_image(image)
        kwargs = dict(
            image=image,
            name=name,
            detach=True,
            privileged=False,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            mem_limit=mem,
            memswap_limit=mem,
            nano_cpus=int(cpus * 1_000_000_000),
            pids_limit=self._s.pids_limit,
            volumes=volumes,
            labels={MANAGED_LABEL: "true", DEPLOYMENT_LABEL: dep_id, ORG_LABEL: org},
            **extra,
        )
        if network:
            kwargs["network"] = network
        return self._client.containers.create(**kwargs)

    def ensure_image(self, image: str) -> None:
        if image not in self._s.images:
            raise ImageNotAllowedError(f"image not in allowlist: {image}")
        try:
            self._client.images.get(image)
        except Exception:  # ImageNotFound (kept broad: the SDK wraps several errors)
            self._client.images.pull(image)

    # ---- provisioning ---------------------------------------------------------

    def create_network(self, dep_id: str, org: str) -> str:
        name = network_name(dep_id)
        # internal: the generated app and its database have no route to the internet.
        self._client.networks.create(
            name,
            driver="bridge",
            internal=True,
            labels={MANAGED_LABEL: "true", DEPLOYMENT_LABEL: dep_id, ORG_LABEL: org},
        )
        self._connect_self(name)
        return name

    def _self_ref(self) -> str:
        return self._s.self_container or socket.gethostname()

    def _connect_self(self, network: str) -> None:
        # The runner doubles as reverse proxy, so it joins each private network.
        self._client.networks.get(network).connect(self._self_ref())

    def create_volume(self, name: str, dep_id: str, org: str) -> None:
        self._client.volumes.create(
            name=name, labels={MANAGED_LABEL: "true", DEPLOYMENT_LABEL: dep_id, ORG_LABEL: org}
        )

    def run_build(self, dep_id: str, org: str, tar_bytes: bytes) -> tuple[int, str]:
        """Unpack the project into its own volume, build it, return (exit code, log tail)."""
        volume = workspace_volume(dep_id)
        self.create_volume(volume, dep_id, org)
        container = self._create(
            image=self._s.build_image,
            name=container_name(dep_id, "build"),
            dep_id=dep_id,
            org=org,
            mem=self._s.build_mem,
            cpus=self._s.build_cpus,
            volumes={
                volume: {"bind": WORKSPACE_DIR, "mode": "rw"},
                self._s.gradle_cache_volume: {"bind": GRADLE_CACHE_DIR, "mode": "rw"},
            },
            command=BUILD_COMMAND,
            working_dir=WORKSPACE_DIR,
            environment={"GRADLE_USER_HOME": GRADLE_CACHE_DIR},
            user="root",  # fresh named volumes are root-owned; every capability is dropped
        )
        container.put_archive(WORKSPACE_DIR, tar_bytes)
        container.start()
        exit_code = self._wait_exit(container, self._s.build_timeout)
        logs = self._tail(container)
        return exit_code, logs

    def start_db(self, dep_id: str, org: str, network: str, password: str) -> str:
        volume = db_volume(dep_id)
        self.create_volume(volume, dep_id, org)
        container = self._create(
            image=self._s.postgres_image,
            name=container_name(dep_id, "db"),
            dep_id=dep_id,
            org=org,
            mem=self._s.db_mem,
            cpus=self._s.db_cpus,
            volumes={volume: {"bind": "/var/lib/postgresql/data", "mode": "rw"}},
            network=network,
            environment={"POSTGRES_DB": "app", "POSTGRES_USER": "app", "POSTGRES_PASSWORD": password},
            healthcheck={
                "test": ["CMD-SHELL", "pg_isready -U app -d app"],
                "interval": 2_000_000_000,
                "timeout": 3_000_000_000,
                "retries": 30,
            },
            # postgres needs its default caps to chown its data dir at first boot.
            cap_add=["CHOWN", "SETUID", "SETGID", "DAC_OVERRIDE", "FOWNER"],
        )
        container.start()
        return container.name

    def wait_db_healthy(self, dep_id: str) -> bool:
        deadline = time.monotonic() + self._s.db_timeout
        while time.monotonic() < deadline:
            container = self._client.containers.get(container_name(dep_id, "db"))
            container.reload()
            state = container.attrs.get("State", {})
            if state.get("Health", {}).get("Status") == "healthy":
                return True
            if state.get("Status") in ("exited", "dead"):
                return False
            self._sleep(1)
        return False

    def start_app(self, dep_id: str, org: str, network: str, password: str) -> str:
        container = self._create(
            image=self._s.runtime_image,
            name=container_name(dep_id, "app"),
            dep_id=dep_id,
            org=org,
            mem=self._s.app_mem,
            cpus=self._s.app_cpus,
            volumes={workspace_volume(dep_id): {"bind": WORKSPACE_DIR, "mode": "ro"}},
            network=network,
            command=["java", "-jar", JAR_PATH],
            user="65534:65534",
            read_only=True,
            tmpfs={"/tmp": "rw,size=128m,mode=1777"},
            environment={
                # The six names the generated application.yml interpolates (same
                # contract as the jvm-boot-smoke compose service).
                "SPRING_APPLICATION_NAME": f"generated-{dep_id[:8]}",
                "SPRING_DATASOURCE_URL": f"jdbc:postgresql://{container_name(dep_id, 'db')}:5432/app",
                "SPRING_DATASOURCE_USERNAME": "app",
                "SPRING_DATASOURCE_PASSWORD": password,
                "JPA_DDL_AUTO": self._s.jpa_ddl_auto,
                "SERVER_PORT": str(self._s.app_port),
                # Behind the runner's reverse proxy: honour X-Forwarded-*.
                "SERVER_FORWARD_HEADERS_STRATEGY": "framework",
                "JAVA_TOOL_OPTIONS": "-XX:MaxRAMPercentage=65 -Xss512k",
            },
        )
        container.start()
        return container.name

    # ---- observation ----------------------------------------------------------

    def app_state(self, dep_id: str) -> str:
        try:
            container = self._client.containers.get(container_name(dep_id, "app"))
            container.reload()
            return container.attrs.get("State", {}).get("Status", "unknown")
        except Exception:
            return "missing"

    def logs_tail(self, name: str) -> str:
        try:
            return self._tail(self._client.containers.get(name))
        except Exception:
            return ""

    def _tail(self, container) -> str:
        raw = container.logs(tail=self._s.log_tail_lines, stdout=True, stderr=True)
        return raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)

    def _wait_exit(self, container, timeout: int) -> int:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            container.reload()
            state = container.attrs.get("State", {})
            if state.get("Status") in ("exited", "dead"):
                return int(state.get("ExitCode", 1))
            self._sleep(2)
        try:
            container.kill()
        except Exception:
            pass
        return 124  # like `timeout(1)`

    # ---- teardown -------------------------------------------------------------

    def remove_deployment(self, dep_id: str) -> None:
        self._remove_by_label(f"{DEPLOYMENT_LABEL}={dep_id}")

    def cleanup_all(self) -> None:
        """Startup sweep: everything this runner ever labelled. The Gradle cache
        volume carries no label, so it survives."""
        self._remove_by_label(f"{MANAGED_LABEL}=true")

    def _remove_by_label(self, label: str) -> None:
        flt = {"label": label}
        for container in self._client.containers.list(all=True, filters=flt):
            try:
                container.remove(force=True, v=True)
            except Exception:
                pass
        for network in self._client.networks.list(filters=flt):
            try:
                network.disconnect(self._self_ref(), force=True)
            except Exception:
                pass  # not connected
            try:
                network.remove()
            except Exception:
                pass
        for volume in self._client.volumes.list(filters=flt):
            try:
                volume.remove(force=True)
            except Exception:
                pass
