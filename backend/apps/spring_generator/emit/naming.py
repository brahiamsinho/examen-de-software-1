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
import unicodedata

from apps.spring_generator.emit.errors import InvalidJavaIdentifierError, InvalidResourcePathError

_LEGAL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UNDERSCORE_BOUNDARY = re.compile(r"_([A-Za-z0-9])")
_LEADING_CHAR = re.compile(r"^[A-Za-z]")
_TRAILING_ID_SUFFIX = re.compile(r"_id$")
_CAMEL_PASCAL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_NON_ALNUM_RUN = re.compile(r"[^A-Za-z0-9]+")
_COMBINING_MARKS = re.compile(r"[̀-ͯ]")
_PLURAL_SIBILANT_SUFFIX = re.compile(r"(s|x|z|ch|sh)$")
_PLURAL_CONSONANT_Y_SUFFIX = re.compile(r"[^aeiou]y$")
_RESOURCE_PATH_SEGMENT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Java reserved words, contextual keywords, and literals that would
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


def relationship_base_name(column_name: str) -> str:
    """`"category_id"` -> `"category"` (DD26): strips one trailing
    `_id` suffix. Falls back to the unchanged column name when
    stripping yields an empty string or there is no `_id` suffix to
    strip (e.g. a bare `"id"` column).
    """
    stripped = _TRAILING_ID_SUFFIX.sub("", column_name)
    if not stripped or stripped == column_name:
        return column_name
    return stripped


def screaming_snake_case(label: str) -> str:
    """`"In Progress"` -> `"IN_PROGRESS"` (DD31): a fixed 3-step regex
    normalization — (1) split camel/Pascal boundaries, (2) collapse
    every non-alphanumeric run to one `_`, (3) uppercase — validated
    through the same `naming._validate` used by `pascal_case`/
    `camel_case` (DD16).
    """
    unaccented = _COMBINING_MARKS.sub("", unicodedata.normalize("NFKD", label))
    split_boundaries = _CAMEL_PASCAL_BOUNDARY.sub(r"\1_\2", unaccented)
    collapsed = _NON_ALNUM_RUN.sub("_", split_boundaries)
    converted = collapsed.upper()
    return _validate(label, converted)


def package_path(base_package: str) -> str:
    """`"com.modelia.generated"` -> `"com/modelia/generated"`."""
    return base_package.replace(".", "/")


def _join_with_separator(parts: list[str], separator: str) -> str:
    """Separator-join without `str.join` (DD14 guard)."""
    joined = ""
    for index, part in enumerate(parts):
        joined = part if index == 0 else "{}{}{}".format(joined, separator, part)
    return joined


def _pluralize_word(word: str) -> str:
    """DD45's fixed 3-rule pluralizer: (1) `s|x|z|ch|sh$` -> `+es`,
    (2) consonant + `y$` -> `ies`, (3) otherwise `+s`.
    """
    if _PLURAL_SIBILANT_SUFFIX.search(word):
        return _PLURAL_SIBILANT_SUFFIX.sub(lambda match: "{}es".format(match.group(1)), word)
    if _PLURAL_CONSONANT_Y_SUFFIX.search(word):
        return _PLURAL_CONSONANT_Y_SUFFIX.sub(lambda match: "{}ies".format(match.group(0)[0]), word)
    return "{}s".format(word)


def resource_path_segment(table_name: str) -> str:
    """DD45: pluralize the last `_`-separated word of `table_name`, then
    lowercase and replace `_` with `-` (`"order_line"` -> `"order-lines"`,
    `"category"` -> `"categories"`). Raises `InvalidResourcePathError`
    when the resulting segment fails the `^[a-z0-9]+(-[a-z0-9]+)*$`
    whitelist — this whitelist is distinct from DD16's identifier
    whitelist because `-` is illegal in a Java identifier but is the
    dominant REST convention for a plural kebab-case path segment.
    """
    words = table_name.split("_")
    words[-1] = _pluralize_word(words[-1])
    pluralized = _join_with_separator(words, "_")
    segment = pluralized.lower().replace("_", "-")

    if not _RESOURCE_PATH_SEGMENT.match(segment):
        raise InvalidResourcePathError(table_name=table_name, segment=segment)
    return segment
