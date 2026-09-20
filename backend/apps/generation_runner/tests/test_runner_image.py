"""DD80: the Gradle runner image tag is derived from `emit/versions.py` only.

The expected value is rebuilt from the imported constants; no version
literal appears here (a restated literal would recreate the bump-drift
failure mode DD62 exists to prevent).
"""
from apps.generation_runner.runner_image import gradle_runner_image
from apps.spring_generator.emit.versions import GRADLE_VERSION, JAVA_VERSION


def test_gradle_runner_image_follows_the_pinned_versions():
    assert gradle_runner_image() == f"gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}"


def test_gradle_runner_image_is_a_single_line_tag_without_whitespace():
    # The host script captures stdout verbatim into GRADLE_IMAGE (DD82).
    image = gradle_runner_image()

    assert image == image.strip()
    assert "\n" not in image
    assert image.startswith("gradle:")
    assert "-jdk" in image
