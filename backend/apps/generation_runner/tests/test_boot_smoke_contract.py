"""DD101: pin the generated-side literals that `scripts/boot-smoke.sh` hardcodes.

The boot smoke drives the sample project's Customer resource over HTTP. It
assumes a URL path, a request key, a response key, status codes and the six
environment names of application.yml. This test fails offline the day the
generator drifts from any of them. It proves nothing about compose wiring, the
JVM or the real HTTP responses: those are proven only by the recorded gate run
(`bash scripts/verify-generated-project.sh`, see gate-evidence.md).

Exit codes of the smoke script, one code per stage (DD105): 6 is transport or
HTTP status (including a non-200 `/v3/api-docs`), 7 is document content (the
OpenAPI body lacks the `"openapi":` field or the `"/api/customers"` path). The
`/v3/api-docs` literal itself is unreachable from pytest (`scripts/` is not
mounted, DD101); this file only pins that the springdoc starter making that
endpoint exist is declared in the generated `build.gradle` (DD106).
"""
import re

from apps.generation_runner.samples.sample_model import build_sample_relational_model
from apps.spring_generator.emit.renderer import generate_project_sources

BASE_PACKAGE = "com.modelia.generated"
JAVA_ROOT = "src/main/java/com/modelia/generated/"
EXPECTED_ENV_NAMES = {
    "SPRING_APPLICATION_NAME",
    "SPRING_DATASOURCE_URL",
    "SPRING_DATASOURCE_USERNAME",
    "SPRING_DATASOURCE_PASSWORD",
    "JPA_DDL_AUTO",
    "SERVER_PORT",
}


def _files() -> dict[str, str]:
    sources = generate_project_sources(build_sample_relational_model(), base_package=BASE_PACKAGE)
    return {generated_file.path: generated_file.contents for generated_file in sources.files}


def _controller() -> str:
    return _files()[JAVA_ROOT + "api/CustomerController.java"]


def _annotated_method(source: str, annotation: str) -> str:
    """Return the annotation block plus the signature line that follows it."""
    match = re.search(re.escape(annotation) + r"\n(?:\s*@\w+.*\n)*\s*public [^\n]+", source)
    assert match is not None, annotation
    return match.group(0)


def test_controller_is_mounted_on_api_customers():
    assert '@RequestMapping("/api/customers")' in _controller()


def test_build_gradle_declares_the_springdoc_starter_behind_v3_api_docs():
    build_gradle = _files()["build.gradle"]

    assert "org.springdoc:springdoc-openapi-starter-webmvc-ui:3.1.1'" in build_gradle


def test_count_endpoint_exists_for_the_readiness_probe():
    assert "public long count()" in _annotated_method(_controller(), '@GetMapping("/count")')


def test_post_creates_with_status_created():
    block = _annotated_method(_controller(), '@PostMapping("")')

    assert "@ResponseStatus(HttpStatus.CREATED)" in block
    assert "@RequestBody CustomerRequestDto" in block


def test_get_by_id_returns_the_response_dto():
    assert "CustomerResponseDto findById" in _annotated_method(_controller(), '@GetMapping("/{id}")')


def test_delete_by_id_answers_no_content():
    block = _annotated_method(_controller(), '@DeleteMapping("/{id}")')

    assert "@ResponseStatus(HttpStatus.NO_CONTENT)" in block
    assert "public void delete" in block


def test_request_dto_takes_full_name_and_never_an_id():
    request_dto = _files()[JAVA_ROOT + "application/dto/CustomerRequestDto.java"]

    assert "private String fullName;" in request_dto
    assert "setFullName" in request_dto
    assert not re.search(r"\bid\b", request_dto)


def test_response_dto_carries_the_id_the_smoke_parses():
    response_dto = _files()[JAVA_ROOT + "application/dto/CustomerResponseDto.java"]

    assert "private UUID id;" in response_dto
    assert "private String fullName;" in response_dto


def test_application_yml_interpolates_exactly_the_six_env_names_without_defaults():
    application_yml = _files()["src/main/resources/application.yml"]
    placeholders = re.findall(r"\$\{([^}]*)\}", application_yml)

    assert set(placeholders) == EXPECTED_ENV_NAMES
    assert len(placeholders) == len(EXPECTED_ENV_NAMES)
