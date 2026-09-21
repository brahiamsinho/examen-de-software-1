"""Runner configuration. Every value comes from the environment (no hardcoded
hosts, ports, images, limits or TTLs); defaults are only sane local values."""
import os
from dataclasses import dataclass, field


class ConfigError(RuntimeError):
    """The runner refuses to start with an unsafe or incomplete configuration."""


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


def _str(name: str, default: str) -> str:
    return os.environ.get(name, "").strip() or default


@dataclass(frozen=True)
class Settings:
    token: str
    public_base_url: str = "http://localhost:8090"
    # Fixed image allowlist: the ONLY images the runner may ever create a
    # container from. Nothing in a request can change these.
    build_image: str = "gradle:9.7.1-jdk21"
    runtime_image: str = "eclipse-temurin:21-jre"
    postgres_image: str = "postgres:16-alpine"
    gradle_cache_volume: str = "modelia-gradle-cache"
    self_container: str = ""  # container the runner itself runs in; "" = hostname
    # Resource limits applied to every container.
    build_mem: str = "1536m"
    app_mem: str = "512m"
    db_mem: str = "256m"
    build_cpus: float = 1.5
    app_cpus: float = 1.0
    db_cpus: float = 0.5
    pids_limit: int = 512
    # Timeouts / lifetime (seconds).
    build_timeout: int = 900
    db_timeout: int = 90
    start_timeout: int = 240
    max_lifetime: int = 6 * 3600
    reaper_interval: int = 60
    # Zip intake limits.
    max_zip_bytes: int = 5 * 1024 * 1024
    max_unpacked_bytes: int = 25 * 1024 * 1024
    max_zip_files: int = 2000
    # Generated app.
    jpa_ddl_auto: str = "update"
    app_port: int = 8080
    max_workers: int = 2
    log_tail_lines: int = 60
    images: frozenset = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "images",
            frozenset({self.build_image, self.runtime_image, self.postgres_image}),
        )

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.environ.get("RUNNER_TOKEN", "").strip()
        if not token:
            raise ConfigError("RUNNER_TOKEN is empty: refusing to start without bearer-token auth.")
        d = cls.__dataclass_fields__
        return cls(
            token=token,
            public_base_url=_str("PUBLIC_BASE_URL", d["public_base_url"].default).rstrip("/"),
            build_image=_str("RUNNER_BUILD_IMAGE", d["build_image"].default),
            runtime_image=_str("RUNNER_RUNTIME_IMAGE", d["runtime_image"].default),
            postgres_image=_str("RUNNER_POSTGRES_IMAGE", d["postgres_image"].default),
            gradle_cache_volume=_str("RUNNER_GRADLE_CACHE_VOLUME", d["gradle_cache_volume"].default),
            self_container=_str("RUNNER_SELF_CONTAINER", ""),
            build_mem=_str("RUNNER_BUILD_MEM", d["build_mem"].default),
            app_mem=_str("RUNNER_APP_MEM", d["app_mem"].default),
            db_mem=_str("RUNNER_DB_MEM", d["db_mem"].default),
            build_cpus=float(_str("RUNNER_BUILD_CPUS", str(d["build_cpus"].default))),
            app_cpus=float(_str("RUNNER_APP_CPUS", str(d["app_cpus"].default))),
            db_cpus=float(_str("RUNNER_DB_CPUS", str(d["db_cpus"].default))),
            pids_limit=_int("RUNNER_PIDS_LIMIT", d["pids_limit"].default),
            build_timeout=_int("RUNNER_BUILD_TIMEOUT", d["build_timeout"].default),
            db_timeout=_int("RUNNER_DB_TIMEOUT", d["db_timeout"].default),
            start_timeout=_int("RUNNER_START_TIMEOUT", d["start_timeout"].default),
            max_lifetime=_int("RUNNER_MAX_LIFETIME_SECONDS", d["max_lifetime"].default),
            reaper_interval=_int("RUNNER_REAPER_INTERVAL", d["reaper_interval"].default),
            max_zip_bytes=_int("RUNNER_MAX_ZIP_BYTES", d["max_zip_bytes"].default),
            max_unpacked_bytes=_int("RUNNER_MAX_UNPACKED_BYTES", d["max_unpacked_bytes"].default),
            max_zip_files=_int("RUNNER_MAX_ZIP_FILES", d["max_zip_files"].default),
            jpa_ddl_auto=_str("RUNNER_JPA_DDL_AUTO", d["jpa_ddl_auto"].default),
            app_port=_int("RUNNER_APP_PORT", d["app_port"].default),
            max_workers=_int("RUNNER_MAX_WORKERS", d["max_workers"].default),
        )
