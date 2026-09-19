"""Pinned toolchain versions (DD62) and the frozen scaffold template
contexts (DD63). Pure data: no template is rendered here.
"""
from dataclasses import FrozenInstanceError

import pytest

from apps.spring_generator.emit.scaffold_context import (
    APPLICATION_CLASS_NAME,
    ApplicationClassContext,
    BuildScriptContext,
    build_application_class_context,
    build_build_script_context,
)
from apps.spring_generator.emit.versions import (
    GRADLE_VERSION,
    JAVA_VERSION,
    PROJECT_VERSION,
    SPRING_BOOT_VERSION,
)


def test_pinned_versions_have_the_spike_verified_values():
    assert SPRING_BOOT_VERSION == "4.1.1"
    assert JAVA_VERSION == 21
    assert PROJECT_VERSION == "0.0.1-SNAPSHOT"
    assert GRADLE_VERSION == "9.7.1"


def test_java_version_is_an_int_not_a_str():
    assert isinstance(JAVA_VERSION, int)
    assert not isinstance(JAVA_VERSION, bool)


def test_build_script_context_carries_group_and_the_pinned_versions():
    context = build_build_script_context(base_package="com.example.generated")

    assert context == BuildScriptContext(
        group="com.example.generated",
        version=PROJECT_VERSION,
        spring_boot_version=SPRING_BOOT_VERSION,
        java_version=JAVA_VERSION,
    )


def test_build_script_context_group_follows_a_different_base_package():
    context = build_build_script_context(base_package="org.example.app")

    assert context.group == "org.example.app"
    assert context.spring_boot_version == "4.1.1"
    assert context.java_version == 21


def test_application_class_context_uses_the_root_package_and_class_name():
    context = build_application_class_context(base_package="com.example.generated")

    assert context == ApplicationClassContext(package="com.example.generated", class_name="Application")
    assert APPLICATION_CLASS_NAME == "Application"


def test_application_class_context_package_follows_a_different_base_package():
    context = build_application_class_context(base_package="app")

    assert context.package == "app"
    assert context.class_name == "Application"


def test_build_script_context_is_frozen():
    context = build_build_script_context(base_package="com.example.generated")

    with pytest.raises(FrozenInstanceError):
        context.group = "other"


def test_application_class_context_is_frozen():
    context = build_application_class_context(base_package="com.example.generated")

    with pytest.raises(FrozenInstanceError):
        context.class_name = "Other"
