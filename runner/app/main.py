"""Modelia runner: builds and runs generated Spring backends, and proxies to them.

Two surfaces on one port:
  * management API (`/deployments...`), bearer-token protected, called only by
    the Django backend over the compose network;
  * public reverse proxy (`/gen/{deployment_id}/...`), the only thing a browser
    (or, in the cloud, Caddy) should reach. The port is bound to loopback by
    default (see docker-compose.yml `RUNNER_BIND`).

Stage 1 mounts the raw Docker socket into THIS service only. Stage 2 replaces it
with a restricted docker-socket-proxy that permits just the calls DockerOps makes.
"""
import re
import secrets
import threading
from contextlib import asynccontextmanager
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from starlette.background import BackgroundTask

from .archive import InvalidArchiveError
from .config import Settings
from .docker_ops import DockerOps, container_name
from .manager import DeploymentExists, DeploymentManager

_ORG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length",
}


def _probe_factory():
    def probe(name: str, port: int) -> bool:
        try:
            return httpx.get(f"http://{name}:{port}/v3/api-docs", timeout=3.0).status_code == 200
        except httpx.HTTPError:
            return False

    return probe


def create_app(settings: Settings, manager: DeploymentManager, *, run_background: bool = True) -> FastAPI:
    stop_event = threading.Event()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.proxy_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0), follow_redirects=False)
        if run_background:
            await run_in_threadpool(manager.startup_cleanup)
            threading.Thread(target=manager.run_reaper, args=(stop_event,), daemon=True).start()
        yield
        stop_event.set()
        await app.state.proxy_client.aclose()

    app = FastAPI(title="Modelia runner", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def require_token(request: Request) -> None:
        header = request.headers.get("authorization", "")
        scheme, _, supplied = header.partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(supplied.encode(), settings.token.encode()):
            raise HTTPException(401, "invalid or missing bearer token", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.put("/deployments/{dep_id}", status_code=202, dependencies=[Depends(require_token)])
    async def start_deployment(dep_id: UUID, org: str, request: Request):
        if not _ORG_RE.match(org):
            raise HTTPException(422, "invalid organization slug")
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > settings.max_zip_bytes:
            raise HTTPException(413, "archive too large")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > settings.max_zip_bytes:
                raise HTTPException(413, "archive too large")
        try:
            deployment = await run_in_threadpool(manager.submit, str(dep_id), org, bytes(body))
        except InvalidArchiveError as exc:
            raise HTTPException(422, str(exc)) from exc
        except DeploymentExists as exc:
            raise HTTPException(409, "deployment id already exists") from exc
        return manager.public_view(deployment)

    @app.get("/deployments/{dep_id}", dependencies=[Depends(require_token)])
    def deployment_status(dep_id: UUID):
        deployment = manager.get(str(dep_id))
        if deployment is None:
            raise HTTPException(404, "unknown deployment")
        return manager.public_view(deployment)

    @app.delete("/deployments/{dep_id}", status_code=204, dependencies=[Depends(require_token)])
    def delete_deployment(dep_id: UUID):
        manager.stop(str(dep_id))

    @app.api_route(
        "/gen/{dep_id}/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def proxy(dep_id: UUID, path: str, request: Request):
        dep = str(dep_id)
        deployment = manager.get(dep)
        if deployment is None or deployment.status == "stopped":
            return JSONResponse({"detail": "unknown deployment"}, status_code=404)
        if deployment.status != "running":
            return JSONResponse({"detail": f"deployment is {deployment.status}"}, status_code=503)

        prefix = f"/gen/{dep}"
        raw = request.scope.get("raw_path", request.url.path.encode()).decode()
        rest = raw[len(prefix):] if raw.startswith(prefix) else f"/{path}"
        query = request.scope.get("query_string", b"").decode()
        upstream = f"http://{container_name(dep, 'app')}:{settings.app_port}{rest or '/'}"
        if query:
            upstream += f"?{query}"

        headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP}
        headers["X-Forwarded-Prefix"] = prefix
        headers["X-Forwarded-Host"] = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        headers["X-Forwarded-Proto"] = request.headers.get("x-forwarded-proto") or request.url.scheme
        headers["X-Forwarded-For"] = request.headers.get("x-forwarded-for") or (
            request.client.host if request.client else ""
        )
        client: httpx.AsyncClient = request.app.state.proxy_client
        try:
            upstream_request = client.build_request(
                request.method, upstream, headers=headers, content=await request.body()
            )
            response = await client.send(upstream_request, stream=True)
        except httpx.HTTPError:
            return JSONResponse({"detail": "the generated application is unreachable"}, status_code=502)
        out_headers = {k: v for k, v in response.headers.items() if k.lower() not in _HOP_BY_HOP}
        return StreamingResponse(
            response.aiter_raw(),
            status_code=response.status_code,
            headers=out_headers,
            background=BackgroundTask(response.aclose),
        )

    @app.get("/gen/{dep_id}")
    def proxy_root_redirect(dep_id: UUID):
        return RedirectResponse(f"/gen/{dep_id}/", status_code=308)

    return app


def build_default_app() -> FastAPI:
    import docker

    settings = Settings.from_env()  # raises ConfigError when RUNNER_TOKEN is empty
    ops = DockerOps(docker.from_env(), settings)
    manager = DeploymentManager(ops, settings, probe=_probe_factory())
    return create_app(settings, manager)
