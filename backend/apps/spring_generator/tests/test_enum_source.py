"""RED->GREEN: `generate_enum_source()` + `Enum.java.j2` (design.md
DD30-DD33).

Covers: output path/package; invalid `base_package` raises `ValueError`;
DD31's SCREAMING_SNAKE_CASE constant normalization; DD32's verbatim
`getLabel()`; zero annotations, no Jackson; correct constant
terminators; balanced braces; determinism; `EmptyEnumTypeError`;
`DuplicateEnumConstantError`; `InvalidJavaIdentifierError`; all three
subclass `UngeneratableSourceError`.
"""
import pytest

from apps.spring_generator.emit.errors import (
    DuplicateEnumConstantError,
    EmptyEnumTypeError,
    InvalidJavaIdentifierError,
    UngeneratableSourceError,
)
from apps.spring_generator.emit.renderer import generate_enum_source
from apps.spring_generator.tests.factories import an_enum_type


def test_generated_file_path_and_package_match_base_package():
    enum_type = an_enum_type(name="order_status")

    generated = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert generated.path == "src/main/java/com/modelia/generated/domain/OrderStatus.java"
    assert "package com.modelia.generated.domain;" in generated.contents


def test_invalid_base_package_raises_value_error():
    enum_type = an_enum_type()

    with pytest.raises(ValueError):
        generate_enum_source(enum_type, base_package="Not_A_Valid_Package!")


@pytest.mark.parametrize(
    "label, expected_constant",
    [
        ("in_progress", "IN_PROGRESS"),
        ("InProgress", "IN_PROGRESS"),
        ("in-progress", "IN_PROGRESS"),
        ("IN PROGRESS", "IN_PROGRESS"),
    ],
)
def test_labels_normalize_to_screaming_snake_case_constants(label, expected_constant):
    enum_type = an_enum_type(name="status", labels=(label,))

    generated = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert "{}(\"{}\")".format(expected_constant, label) in generated.contents


def test_get_label_returns_the_verbatim_label():
    enum_type = an_enum_type(name="status", labels=("in_progress",))

    generated = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert 'public String getLabel()' in generated.contents
    assert '"in_progress"' in generated.contents


def test_no_annotations_and_no_jackson_reference():
    enum_type = an_enum_type()

    generated = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert "@" not in generated.contents
    assert "com.fasterxml.jackson" not in generated.contents


def test_last_constant_terminated_by_semicolon_others_by_comma():
    enum_type = an_enum_type(name="order_status", labels=("PENDING", "PAID", "SHIPPED"))

    generated = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert 'PENDING("PENDING"),' in generated.contents
    assert 'PAID("PAID"),' in generated.contents
    assert 'SHIPPED("SHIPPED");' in generated.contents


def test_braces_are_balanced():
    enum_type = an_enum_type()

    generated = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert generated.contents.count("{") == generated.contents.count("}")


def test_repeated_generation_is_byte_identical():
    enum_type = an_enum_type()

    first = generate_enum_source(enum_type, base_package="com.modelia.generated")
    second = generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert first == second
    assert first.contents == second.contents


def test_empty_labels_raises_empty_enum_type_error():
    enum_type = an_enum_type(labels=())

    with pytest.raises(EmptyEnumTypeError) as excinfo:
        generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert isinstance(excinfo.value, UngeneratableSourceError)


def test_colliding_labels_raise_duplicate_enum_constant_error():
    enum_type = an_enum_type(name="status", labels=("in progress", "in-progress"))

    with pytest.raises(DuplicateEnumConstantError) as excinfo:
        generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert isinstance(excinfo.value, UngeneratableSourceError)


def test_illegal_label_raises_invalid_java_identifier_error():
    enum_type = an_enum_type(name="status", labels=("1st",))

    with pytest.raises(InvalidJavaIdentifierError) as excinfo:
        generate_enum_source(enum_type, base_package="com.modelia.generated")

    assert isinstance(excinfo.value, UngeneratableSourceError)
