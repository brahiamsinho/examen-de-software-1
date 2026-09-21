"""Names typed in the diagram (spaces, accents, dashes, leading digits)
must map to valid snake_case DB identifiers without touching the model."""
import pytest

from apps.relational_mapping.mapping.errors import InvalidElementNameError
from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.relational_mapping.mapping.naming import snake_case
from apps.relational_mapping.tests.factories import a_class, a_model, an_attribute


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("OrderLine", "order_line"),  # already valid: unchanged behaviour
        ("order_line", "order_line"),
        ("Class B", "class_b"),
        ("  Class   B  ", "class_b"),
        ("Orden de Compra", "orden_de_compra"),
        ("Órden Ñandú", "orden_nandu"),
        ("order-line", "order_line"),
        ("Price ($)", "price"),
        ("2fa Code", "n_2fa_code"),
        ("class", "class"),  # Java keyword handling belongs to the emitter
    ],
)
def test_snake_case_normalizes_non_identifier_characters(typed, expected):
    assert snake_case(typed) == expected


def test_name_without_any_usable_character_is_rejected():
    with pytest.raises(InvalidElementNameError):
        snake_case("日本")


def test_spaced_names_map_to_valid_tables_and_columns_keeping_the_model_untouched():
    klass = a_class(name="Class B", attributes=(an_attribute(name="Fecha de Nacimiento"),))

    table = map_to_relational(a_model(classes=(klass,))).table_by_name("class_b")

    assert table.column_by_name("fecha_de_nacimiento") is not None
    assert klass.name == "Class B"


def test_names_that_normalize_to_the_same_identifier_are_disambiguated_deterministically():
    model = a_model(classes=(a_class(name="Class A"), a_class(name="class-a")))

    names = sorted(table.name for table in map_to_relational(model).tables)

    assert names == ["class_a", "class_a_2"]
