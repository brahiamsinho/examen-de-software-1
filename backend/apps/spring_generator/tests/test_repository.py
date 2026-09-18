"""RED: apps.spring_generator.emit.renderer does not exist yet.

Covers: `interface <E>Repository extends JpaRepository<<E>, UUID>`,
empty body, no `@Repository`, correct entity import (design.md DD17).
"""
from apps.relational_mapping.domain.schema import Column, PrimaryKey
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources
from apps.spring_generator.tests.factories import a_table


def _product_table():
    return a_table(
        name="product",
        columns=(Column(name="id", type=ColumnType.UUID, nullable=False),),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
    )


def _repository_source():
    sources = generate_table_sources(_product_table(), base_package="com.modelia.generated")
    path = "src/main/java/com/modelia/generated/persistence/ProductRepository.java"
    return sources.file_by_path(path).contents


def test_repository_interface_signature():
    source = _repository_source()

    assert "public interface ProductRepository extends JpaRepository<Product, UUID> {" in source


def test_repository_has_empty_body():
    source = _repository_source()

    body = source[source.index("{") + 1 : source.rindex("}")]
    assert body.strip() == ""


def test_repository_has_no_repository_annotation():
    source = _repository_source()

    assert "@Repository" not in source


def test_repository_imports_entity_and_jpa_repository():
    source = _repository_source()

    assert "import com.modelia.generated.domain.Product;" in source
    assert "import org.springframework.data.jpa.repository.JpaRepository;" in source
    assert "import java.util.UUID;" in source


def test_repository_braces_are_balanced():
    source = _repository_source()

    assert source.count("{") == source.count("}")
