"""Contract of `generate_project_scaffold_sources` (change
`2026-09-19-spring-boot-project-scaffold`, DD61-DD73).

The three expected file bodies below are the slice-0 spike oracle: the exact
`build.gradle`, `settings.gradle` and `Application.java` that built and booted
for real. Pinned versions are injected with `.format()` from the single
versions module (DD62); the doubled braces are Groovy/Java braces escaped for
`str.format`.
"""
import re
from pathlib import Path

import pytest

from apps.spring_generator.domain.sources import GeneratedSources
from apps.spring_generator.emit import renderer
from apps.spring_generator.emit.versions import (
    JAVA_VERSION,
    PROJECT_VERSION,
    SPRING_BOOT_VERSION,
    SPRINGDOC_VERSION,
)

_EMIT_DIR = Path(__file__).resolve().parent.parent / "emit"
_TEMPLATES_DIR = _EMIT_DIR / "templates"
_SCAFFOLD_TEMPLATES = ("build.gradle.j2", "settings.gradle.j2", "Application.java.j2")

_BUILD_GRADLE_ORACLE = """plugins {{
    id 'java'
    id 'org.springframework.boot' version '{spring_boot_version}'
}}

group = '{group}'
version = '{version}'

java {{
    toolchain {{
        languageVersion = JavaLanguageVersion.of({java_version})
    }}
}}

repositories {{
    mavenCentral()
}}

dependencies {{
    implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)
    implementation 'org.springframework.boot:spring-boot-starter-webmvc'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:{springdoc_version}'
    runtimeOnly 'org.postgresql:postgresql'
}}
"""

_SETTINGS_GRADLE_ORACLE = """rootProject.name = 'generated-backend'
"""

_APPLICATION_JAVA_ORACLE = """package {package};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {{
    public static void main(String[] args) {{
        SpringApplication.run(Application.class, args);
    }}
}}
"""


def _expected_build_gradle(group: str) -> str:
    return _BUILD_GRADLE_ORACLE.format(
        spring_boot_version=SPRING_BOOT_VERSION,
        group=group,
        version=PROJECT_VERSION,
        java_version=JAVA_VERSION,
        springdoc_version=SPRINGDOC_VERSION,
    )


def _scaffold(base_package: str = "com.example.generated") -> GeneratedSources:
    return renderer.generate_project_scaffold_sources(base_package=base_package)


def _by_path(sources: GeneratedSources) -> dict[str, str]:
    return dict(sources.as_mapping())


# ---- exact files, order, content -------------------------------------------------


def test_entry_point_is_public_and_returns_generated_sources():
    assert isinstance(_scaffold(), GeneratedSources)


def test_scaffold_yields_exactly_three_files_in_fixed_order():
    paths = [generated_file.path for generated_file in _scaffold().files]

    assert paths == [
        "build.gradle",
        "settings.gradle",
        "src/main/java/com/example/generated/Application.java",
    ]


def test_single_segment_base_package_places_application_at_the_shortest_path():
    paths = [generated_file.path for generated_file in _scaffold("app").files]

    assert paths == ["build.gradle", "settings.gradle", "src/main/java/app/Application.java"]


def test_default_base_package_matches_the_other_entry_points():
    sources = renderer.generate_project_scaffold_sources()

    assert sources.files[2].path == "src/main/java/com/modelia/generated/Application.java"


def test_build_gradle_equals_the_spike_oracle():
    files = _by_path(_scaffold("com.example.generated"))

    assert files["build.gradle"] == _expected_build_gradle("com.example.generated")


def test_settings_gradle_equals_the_spike_oracle():
    files = _by_path(_scaffold("com.example.generated"))

    assert files["settings.gradle"] == _SETTINGS_GRADLE_ORACLE


def test_application_java_equals_the_spike_oracle():
    files = _by_path(_scaffold("com.example.generated"))

    assert files["src/main/java/com/example/generated/Application.java"] == _APPLICATION_JAVA_ORACLE.format(
        package="com.example.generated"
    )


def test_group_and_package_propagate_from_base_package():
    files = _by_path(_scaffold("org.example.app"))

    assert files["build.gradle"] == _expected_build_gradle("org.example.app")
    assert files["src/main/java/org/example/app/Application.java"] == _APPLICATION_JAVA_ORACLE.format(
        package="org.example.app"
    )
    assert "group = 'org.example.app'" in files["build.gradle"]
    assert "package org.example.app;" in files["src/main/java/org/example/app/Application.java"]


def test_application_package_equals_build_group():
    files = _by_path(_scaffold("com.example.generated"))

    assert "group = 'com.example.generated'" in files["build.gradle"]
    assert "package com.example.generated;" in files["src/main/java/com/example/generated/Application.java"]


# ---- excluded artifacts ------------------------------------------------------------


@pytest.mark.parametrize(
    "excluded",
    [
        ".gitignore",
        "gradlew",
        "gradle/wrapper",
        "Dockerfile",
        "springdoc-openapi-starter-webmvc-ui",
        "spring-boot-starter-actuator",
        "io.spring.dependency-management",
        "build.gradle.kts",
    ],
)
def test_excluded_artifacts_are_absent_from_paths_and_contents(excluded):
    sources = _scaffold()

    assert not any(excluded in generated_file.path for generated_file in sources.files)
    assert not any(excluded in generated_file.contents for generated_file in sources.files)


def test_build_gradle_declares_the_springdoc_starter_at_the_pinned_version():
    contents = _by_path(_scaffold())["build.gradle"]
    starter = f"    implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:{SPRINGDOC_VERSION}'\n"

    assert starter in contents
    assert SPRINGDOC_VERSION == "3.1.1"
    # springdoc sits after the Boot starters and before the runtime driver (DD104).
    assert contents.index("spring-boot-starter-validation") < contents.index(starter)
    assert contents.index(starter) < contents.index("runtimeOnly 'org.postgresql:postgresql'")
    assert contents.count("springdoc-openapi") == 1


# ---- LF and Jinja safety ---------------------------------------------------------------


def test_every_file_is_lf_with_exactly_one_trailing_newline():
    files = _scaffold().files

    assert len(files) == 3
    for generated_file in files:
        assert "\r" not in generated_file.contents
        assert generated_file.contents.endswith("\n")
        assert not generated_file.contents.endswith("\n\n")


def test_no_rendered_file_contains_a_jinja_delimiter():
    files = _scaffold().files

    assert len(files) == 3
    for generated_file in files:
        for delimiter in ("{{", "{%", "{#", "}}", "%}", "#}"):
            assert delimiter not in generated_file.contents


def test_scaffold_templates_contain_no_block_or_comment_tags():
    for template_name in _SCAFFOLD_TEMPLATES:
        source = (_TEMPLATES_DIR / template_name).read_text(encoding="utf-8")

        assert "{%" not in source
        assert "{#" not in source


# ---- base_package validation ---------------------------------------------------------------


@pytest.mark.parametrize("invalid", ["Com.Bad", "com-example", "com..example", "", "1bad"])
def test_invalid_base_package_is_rejected_without_output(invalid):
    with pytest.raises(ValueError):
        renderer.generate_project_scaffold_sources(base_package=invalid)


def test_repeated_scaffold_generation_is_byte_identical():
    first = _scaffold("com.example.generated")
    second = _scaffold("com.example.generated")

    assert first == second
    assert [f.contents for f in first.files] == [f.contents for f in second.files]


# ---- DD72: versions live in one place ------------------------------------------------------------


def _emit_sources_except_versions() -> list[Path]:
    python_modules = [path for path in sorted(_EMIT_DIR.rglob("*.py")) if path.name != "versions.py"]
    templates = sorted(_TEMPLATES_DIR.glob("*.j2"))
    return python_modules + templates


def test_version_scan_covers_python_modules_and_every_template():
    scanned = {path.name for path in _emit_sources_except_versions()}

    assert "renderer.py" in scanned
    assert "scaffold_context.py" in scanned
    assert "versions.py" not in scanned
    assert set(_SCAFFOLD_TEMPLATES) <= scanned


@pytest.mark.parametrize(
    "literal_pattern",
    [r"\b4\.1\.1\b", r"\b9\.7\.1\b", r"\b21\b", r"\b3\.1\.1\b"],
    ids=["spring-boot-version", "gradle-version", "toolchain-version", "springdoc-version"],
)
def test_no_pinned_version_literal_is_restated_outside_the_versions_module(literal_pattern):
    offenders = [
        path.name
        for path in _emit_sources_except_versions()
        if re.search(literal_pattern, path.read_text(encoding="utf-8"))
    ]

    assert offenders == []


# ---- DD73: no hardcoded deployable value ------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden",
    ["localhost", "http://", "https://", "jdbc:", "5432", "8080", "0.0.0.0", "127.0.0.1", "password", "secret", "username"],
)
def test_no_scaffold_file_hardcodes_a_deployable_value(forbidden):
    files = _scaffold().files

    assert len(files) == 3
    for generated_file in files:
        assert forbidden not in generated_file.contents.lower()


def test_no_scaffold_file_contains_an_absolute_or_drive_path():
    absolute_path = re.compile(r"""(?:[A-Za-z]:[\\/])|(?:(?:^|[\s'"(=])/[A-Za-z])""", re.MULTILINE)

    for generated_file in _scaffold().files:
        assert absolute_path.search(generated_file.contents) is None


def test_build_gradle_declares_only_maven_central():
    contents = _by_path(_scaffold())["build.gradle"]

    assert "repositories {\n    mavenCentral()\n}\n" in contents
    assert contents.count("mavenCentral()") == 1
    for other_repository in ("maven {", "mavenLocal", "google()", "jcenter", "url ", "url="):
        assert other_repository not in contents


def test_postgres_driver_coordinate_is_the_only_postgres_mention():
    # DD73: `postgres` is deliberately not in the forbidden list because
    # `org.postgresql:postgresql` is a Maven coordinate, not a deployable value.
    contents = _by_path(_scaffold())["build.gradle"]

    assert "runtimeOnly 'org.postgresql:postgresql'" in contents
    assert contents.lower().count("postgres") == 2
