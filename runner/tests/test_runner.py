import httpx
import pytest
from fastapi.testclient import TestClient

from app.archive import InvalidArchiveError, zip_to_tar
from app.config import ConfigError, Settings
from app.docker_ops import DockerOps, ImageNotAllowedError
from app.main import create_app
from tests.conftest import DEP, make_zip

ZIP = make_zip({"proj/build.gradle": b"plugins {}", "proj/src/App.java": b"class App {}"})
LIMITS = dict(max_zip_bytes=1000, max_unpacked_bytes=1000, max_files=10)


# --- archive intake -------------------------------------------------------------

def test_zip_is_repacked_without_its_top_folder():
    import io, tarfile

    tar = tarfile.open(fileobj=io.BytesIO(zip_to_tar(ZIP, **LIMITS)))
    assert sorted(tar.getnames()) == ["build.gradle", "src/App.java"]


@pytest.mark.parametrize(
    "data, limits",
    [
        (make_zip({"p/../../etc/passwd": b"x"}), LIMITS),  # path traversal
        (make_zip({"/abs/file": b"x"}), LIMITS),  # absolute path
        (make_zip({"p/a": b"x" * 600, "p/b": b"x" * 600}), LIMITS),  # unpacked cap
        (ZIP, {**LIMITS, "max_zip_bytes": 10}),  # oversize archive
        (b"not a zip", LIMITS),
    ],
)
def test_bad_archives_are_rejected(data, limits):
    with pytest.raises(InvalidArchiveError):
        zip_to_tar(data, **limits)


# --- docker safety contract -------------------------------------------------------

def test_full_pipeline_reaches_running_with_hardened_containers(manager, docker):
    manager.submit(DEP, "acme", ZIP)

    assert manager.get(DEP).status == "running"
    assert set(docker.containers_by_name) == {f"modelia-dep-{DEP}-{r}" for r in ("build", "db", "app")}
    for container in docker.containers_by_name.values():
        kw = container.kwargs
        assert kw["image"] in manager._s.images  # fixed allowlist
        assert kw["privileged"] is False and kw["cap_drop"] == ["ALL"]
        assert "no-new-privileges" in kw["security_opt"]
        assert kw["mem_limit"] and kw["nano_cpus"] and kw["pids_limit"]
        assert kw["labels"]["modelia.deployment"] == DEP and kw["labels"]["modelia.org"] == "acme"
        assert kw.get("network_mode") != "host"
        assert all("/" not in source for source in kw["volumes"])  # named volumes only
    app_env = docker.containers_by_name[f"modelia-dep-{DEP}-app"].kwargs["environment"]
    assert app_env["SERVER_FORWARD_HEADERS_STRATEGY"] == "framework"
    assert docker.created_networks[0][1]["internal"] is True
    assert docker.connected == [(f"modelia-dep-{DEP}", "runner-self")]


def test_failed_build_marks_failed_and_cleans_up(manager, docker):
    docker.build_exit_code = 1
    manager.submit(DEP, "acme", ZIP)

    view = manager.public_view(manager.get(DEP))
    assert view["status"] == "failed" and "exit code 1" in view["error"]
    assert "line two" in view["log_tail"]
    assert f"modelia-dep-{DEP}-app" not in docker.containers_by_name  # never started


@pytest.mark.parametrize("kind", ["image", "volume"])
def test_ops_refuses_anything_outside_the_allowlist(settings, docker, kind):
    ops = DockerOps(docker, settings)
    bad = {"image": ("evil:latest", {}), "volume": (settings.build_image, {"/etc": {"bind": "/x"}})}[kind]
    with pytest.raises(ImageNotAllowedError):
        ops._create(image=bad[0], name="modelia-x", dep_id=DEP, org="acme",
                    mem="64m", cpus=0.5, volumes=bad[1])


def test_stop_is_idempotent_and_reaper_expires_old_deployments(manager, docker):
    manager.submit(DEP, "acme", ZIP)
    manager.get(DEP).created_at -= manager._s.max_lifetime + 1

    assert manager.reap_expired() == [DEP]
    manager.stop(DEP)  # second stop must not raise
    assert manager.get(DEP).status == "stopped"


# --- HTTP surface -------------------------------------------------------------------

@pytest.fixture
def client(manager, settings):
    with TestClient(create_app(settings, manager, run_background=False)) as test_client:
        yield test_client


AUTH = {"Authorization": "Bearer secret-token"}


def test_management_api_requires_the_bearer_token(client):
    assert client.get(f"/deployments/{DEP}").status_code == 401
    assert client.get(f"/deployments/{DEP}", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert client.get(f"/deployments/{DEP}", headers=AUTH).status_code == 404


def test_put_validates_id_org_and_archive(client):
    assert client.put("/deployments/not-a-uuid?org=acme", content=ZIP, headers=AUTH).status_code == 422
    assert client.put(f"/deployments/{DEP}?org=../x", content=ZIP, headers=AUTH).status_code == 422
    assert client.put(f"/deployments/{DEP}?org=acme", content=b"junk", headers=AUTH).status_code == 422
    ok = client.put(f"/deployments/{DEP}?org=acme", content=ZIP, headers=AUTH)
    assert ok.status_code == 202 and ok.json()["public_path"] == f"/gen/{DEP}/"


def test_proxy_strips_the_prefix_and_sends_forwarded_prefix(client, manager):
    client.put(f"/deployments/{DEP}?org=acme", content=ZIP, headers=AUTH)
    seen = {}

    def upstream(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["prefix"] = request.headers["x-forwarded-prefix"]
        return httpx.Response(200, stream=httpx.ByteStream(b"[]"))  # a real, unread stream

    client.app.state.proxy_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
    response = client.get(f"/gen/{DEP}/api/customers?page=1")

    assert response.status_code == 200
    assert seen["url"] == f"http://modelia-dep-{DEP}-app:8080/api/customers?page=1"
    assert seen["prefix"] == f"/gen/{DEP}"


def test_runner_refuses_to_start_without_a_token(monkeypatch):
    monkeypatch.setenv("RUNNER_TOKEN", "  ")
    with pytest.raises(ConfigError):
        Settings.from_env()
