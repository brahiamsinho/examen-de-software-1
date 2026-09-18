"""RED: apps.spring_generator.emit.naming does not exist yet.

Covers: `pascal_case`/`camel_case`/`package_path` conversions, Java
reserved-word handling (trailing `_`, DB name preserved via
`@Column(name=...)` elsewhere), and illegal-name rejection (DD16).
"""
import pytest

from apps.spring_generator.emit.errors import InvalidJavaIdentifierError
from apps.spring_generator.emit.naming import camel_case, package_path, pascal_case


def test_pascal_case_converts_snake_case():
    assert pascal_case("order_line") == "OrderLine"


def test_pascal_case_converts_single_word():
    assert pascal_case("product") == "Product"


def test_camel_case_converts_snake_case():
    assert camel_case("order_line") == "orderLine"


def test_camel_case_converts_single_word():
    assert camel_case("product") == "product"


def test_package_path_converts_dotted_package():
    assert package_path("com.modelia.generated") == "com/modelia/generated"


@pytest.mark.parametrize("reserved", ["class", "public", "native", "interface", "package"])
def test_camel_case_reserved_word_gets_trailing_underscore(reserved):
    result = camel_case(reserved)

    assert result == f"{reserved}_"


def test_camel_case_reserved_word_result_is_still_a_legal_identifier():
    # "class" -> "class_" must itself pass the identifier whitelist.
    result = camel_case("class")

    assert result.isidentifier()


@pytest.mark.parametrize("illegal", ["1order", "order-line", "", "order line"])
def test_pascal_case_illegal_name_raises(illegal):
    with pytest.raises(InvalidJavaIdentifierError):
        pascal_case(illegal)


@pytest.mark.parametrize("illegal", ["1order", "order-line", "", "order line"])
def test_camel_case_illegal_name_raises(illegal):
    with pytest.raises(InvalidJavaIdentifierError):
        camel_case(illegal)
