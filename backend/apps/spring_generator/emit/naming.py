"""Java identifier safety (design.md DD16).

`pascal_case`/`camel_case` accept only `[A-Za-z_][A-Za-z0-9_]*` after
conversion; anything else raises `InvalidJavaIdentifierError`. A Java
reserved word gets a trailing `_` (a legal Java identifier) rather
than being rejected outright, so a legitimately-named UML attribute
stays generatable — the original DB name is preserved separately by
each template's explicit `@Column(name=...)`.

Per the DD14 guard: conversion uses `re.sub` (a single declarative
regex substitution), never manual `+`/`.join`/`%`/f-string
concatenation of the generator's own Python source.
"""
import re

from apps.spring_generator.emit.errors import InvalidJavaIdentifierError

_LEGAL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UNDERSCORE_BOUNDARY = re.compile(r"_([A-Za-z0-9])")
_LEADING_CHAR = re.compile(r"^[A-Za-z]")

# Java 21 reserved words, contextual keywords, and literals that would
# otherwise collide with a generated field/method name.
_JAVA_RESERVED_WORDS = frozenset(
    {
        "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class",
        "const", "continue", "default", "do", "double", "else", "enum", "extends", "final",
        "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int",
        "interface", "long", "native", "new", "package", "private", "protected", "public",
        "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
        "throw", "throws", "transient", "try", "void", "volatile", "while", "true", "false",
        "null", "var", "yield", "record", "sealed", "permits", "non-sealed", "_",
    }
)


def _uppercase_match(match: re.Match) -> str:
    return match.group(1).upper()


def _lowercase_match(match: re.Match) -> str:
    return match.group(0).lower()


def _validate(source_name: str, converted: str) -> str:
    if not _LEGAL_IDENTIFIER.match(converted):
        raise InvalidJavaIdentifierError(source_name=source_name, converted=converted)
    if converted in _JAVA_RESERVED_WORDS:
        converted = "{}_".format(converted)
        if not _LEGAL_IDENTIFIER.match(converted):
            raise InvalidJavaIdentifierError(source_name=source_name, converted=converted)
    return converted


def pascal_case(snake: str) -> str:
    """`"order_line"` -> `"OrderLine"` (DD16)."""
    with_boundaries_upper = _UNDERSCORE_BOUNDARY.sub(_uppercase_match, snake)
    converted = _LEADING_CHAR.sub(lambda match: match.group(0).upper(), with_boundaries_upper)
    return _validate(snake, converted)


def camel_case(snake: str) -> str:
    """`"order_line"` -> `"orderLine"` (DD16). A Java reserved word
    (e.g. `"class"`) becomes `"class_"`.
    """
    with_boundaries_upper = _UNDERSCORE_BOUNDARY.sub(_uppercase_match, snake)
    converted = _LEADING_CHAR.sub(_lowercase_match, with_boundaries_upper)
    return _validate(snake, converted)


def package_path(base_package: str) -> str:
    """`"com.modelia.generated"` -> `"com/modelia/generated"`."""
    return base_package.replace(".", "/")
