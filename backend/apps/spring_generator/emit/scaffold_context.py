"""Frozen template contexts for the project scaffold (DD63).

Sibling of `inheritance_context.py`: the scaffold has no column, type
mapping, or import grouping in common with `context.py`, so its contexts
live in their own module. Builders are total and allocation-only; every
version comes from `emit/versions.py` (DD62).
"""
from dataclasses import dataclass

from apps.spring_generator.emit.versions import (
    JAVA_VERSION,
    PROJECT_VERSION,
    SPRING_BOOT_VERSION,
    SPRINGDOC_VERSION,
)

APPLICATION_CLASS_NAME = "Application"


@dataclass(frozen=True)
class BuildScriptContext:
    group: str  # == base_package
    version: str  # PROJECT_VERSION
    spring_boot_version: str  # SPRING_BOOT_VERSION
    java_version: int  # JAVA_VERSION
    springdoc_version: str  # SPRINGDOC_VERSION


@dataclass(frozen=True)
class ApplicationClassContext:
    package: str  # == base_package (root package, DD67)
    class_name: str  # APPLICATION_CLASS_NAME


def build_build_script_context(*, base_package: str) -> BuildScriptContext:
    return BuildScriptContext(
        group=base_package,
        version=PROJECT_VERSION,
        spring_boot_version=SPRING_BOOT_VERSION,
        java_version=JAVA_VERSION,
        springdoc_version=SPRINGDOC_VERSION,
    )


def build_application_class_context(*, base_package: str) -> ApplicationClassContext:
    return ApplicationClassContext(package=base_package, class_name=APPLICATION_CLASS_NAME)
