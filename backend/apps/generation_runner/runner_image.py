"""Gradle runner image tag (design.md DD80).

Reads only `emit/versions.py`, the single source of every generated-project
toolchain version (DD62). Compose cannot import Python, so the host script
calls this function to compute the tag it exports as `GRADLE_IMAGE`.
"""
from apps.spring_generator.emit.versions import GRADLE_VERSION, JAVA_VERSION


def gradle_runner_image() -> str:
    return f"gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}"
