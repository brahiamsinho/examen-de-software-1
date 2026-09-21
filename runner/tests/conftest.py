"""Test doubles: a tiny in-memory Docker client (no Engine needed)."""
import io
import zipfile

import pytest

from app.config import Settings
from app.docker_ops import DockerOps
from app.manager import DeploymentManager

DEP = "11111111-2222-3333-4444-555555555555"


class FakeContainer:
    def __init__(self, name, kwargs, docker):
        self.name = name
        self.kwargs = kwargs
        self._docker = docker
        self.archive = None
        self.attrs = {"State": {"Status": "created"}}

    def put_archive(self, path, data):
        self.archive = (path, data)

    def start(self):
        state = {"Status": "running"}
        if self.name.endswith("-db"):
            state["Health"] = {"Status": "healthy"}
        if self.name.endswith("-build"):
            state = {"Status": "exited", "ExitCode": self._docker.build_exit_code}
        if self.name.endswith("-app") and self._docker.app_crashes:
            state = {"Status": "exited", "ExitCode": 1}
        self.attrs = {"State": state}

    def reload(self):
        pass

    def logs(self, **_):
        return b"line one\nline two"

    def kill(self):
        pass

    def remove(self, **_):
        self._docker.removed.append(self.name)


class FakeDocker:
    def __init__(self):
        self.build_exit_code = 0
        self.app_crashes = False
        self.removed = []
        self.containers_by_name = {}
        self.created_volumes = []
        self.created_networks = []
        self.connected = []
        docker = self

        class Containers:
            def create(self, **kwargs):
                container = FakeContainer(kwargs["name"], kwargs, docker)
                docker.containers_by_name[kwargs["name"]] = container
                return container

            def get(self, name):
                return docker.containers_by_name[name]

            def list(self, **_):
                return list(docker.containers_by_name.values())

        class Networks:
            def create(self, name, **kwargs):
                docker.created_networks.append((name, kwargs))

            def get(self, name):
                net = type("Net", (), {})()
                net.connect = lambda ref: docker.connected.append((name, ref))
                return net

            def list(self, **_):
                return []

        class Volumes:
            def create(self, name, **kwargs):
                docker.created_volumes.append((name, kwargs))

            def list(self, **_):
                return []

        class Images:
            def get(self, _image):
                return object()

            def pull(self, _image):
                raise AssertionError("allowlisted images are present in these tests")

        self.containers = Containers()
        self.networks = Networks()
        self.volumes = Volumes()
        self.images = Images()


class InlineExecutor:
    def submit(self, fn, *args):
        fn(*args)


def make_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


@pytest.fixture
def settings():
    return Settings(token="secret-token", self_container="runner-self")


@pytest.fixture
def docker():
    return FakeDocker()


@pytest.fixture
def manager(docker, settings):
    ops = DockerOps(docker, settings, sleep=lambda _s: None)
    return DeploymentManager(
        ops, settings, probe=lambda _name, _port: True, sleep=lambda _s: None, executor=InlineExecutor()
    )
