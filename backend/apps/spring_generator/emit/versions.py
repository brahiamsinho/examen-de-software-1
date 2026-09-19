"""Single pinned source of every generated-project toolchain version (DD62).

No other module, template, test, compose file, or script may restate one of
these literals; `tests/test_project_scaffold_sources.py` enforces that by
source scan (DD72). Bumping a version is a deliberate, reviewable one-line
change that slices 2-3 re-verify by compiling and booting.
"""
from typing import Final

SPRING_BOOT_VERSION: Final[str] = "4.1.1"
"""Spring Boot Gradle plugin and BOM version (spike oracle: BUILD SUCCESSFUL)."""

JAVA_VERSION: Final[int] = 21
"""Java toolchain language version. `int`, not `str`, because the template
renders it into `JavaLanguageVersion.of({{ java_version }})`, which takes an
int — quoting it would be a Groovy type error."""

PROJECT_VERSION: Final[str] = "0.0.1-SNAPSHOT"
"""`version` of the generated Gradle project."""

GRADLE_VERSION: Final[str] = "9.7.1"
"""Gradle required to build the generated project. Nothing in this slice
renders it (no wrapper is emitted, DD65); slice 2's `gradle:9.7.1-jdk21`
runner image reads it from here (DD62)."""
