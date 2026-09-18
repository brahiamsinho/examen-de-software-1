"""RED: apps.spring_generator.emit.renderer does not exist yet.

Covers: `@Entity`/`@Table(name=...)`, protected no-arg constructor,
getter+setter per field, no Lombok, no `equals`/`hashCode`, no Jackson
import (design.md DD18, DD19). Structural assertions only, per proposal
D2 — no `javac`, no Java parser.
"""
from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources
from apps.spring_generator.tests.factories import a_table


def _product_table():
    return a_table(
        name="product",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="name", type=ColumnType.VARCHAR, nullable=False, length=255),
            Column(name="price", type=ColumnType.NUMERIC, nullable=False, precision=10, scale=2),
        ),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )


def _entity_source():
    sources = generate_table_sources(_product_table(), base_package="com.modelia.generated")
    return sources.file_by_path("src/main/java/com/modelia/generated/domain/Product.java").contents


def test_entity_has_entity_and_table_annotations():
    source = _entity_source()

    assert "@Entity" in source
    assert '@Table(name = "product")' in source
    assert "public class Product {" in source


def test_entity_has_protected_no_arg_constructor():
    source = _entity_source()

    assert "protected Product() {" in source


def test_entity_has_getter_and_setter_per_field():
    source = _entity_source()

    assert "public String getName() {" in source
    assert "public void setName(String name) {" in source
    assert "public BigDecimal getPrice() {" in source
    assert "public void setPrice(BigDecimal price) {" in source


def test_entity_has_no_lombok():
    source = _entity_source()

    assert "lombok" not in source.lower()
    assert "@Getter" not in source
    assert "@Setter" not in source
    assert "@Data" not in source


def test_entity_has_no_equals_or_hash_code():
    source = _entity_source()

    assert "equals(" not in source
    assert "hashCode(" not in source


def test_entity_has_no_jackson_import():
    source = _entity_source()

    assert "com.fasterxml.jackson" not in source


def test_entity_braces_are_balanced():
    source = _entity_source()

    assert source.count("{") == source.count("}")
