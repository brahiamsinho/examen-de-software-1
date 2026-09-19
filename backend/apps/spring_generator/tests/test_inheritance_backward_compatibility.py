import hashlib

from apps.relational_mapping.domain.schema import Column, ForeignKey, PrimaryKey, Table
from apps.relational_mapping.domain.types import ColumnType
from apps.spring_generator.emit.renderer import generate_table_sources


def _product_table() -> Table:
    category_fk = ForeignKey(
        name="fk_product__category_id",
        column_names=("category_id",),
        referenced_table="category",
        referenced_column_names=("id",),
    )
    return Table(
        name="product",
        columns=(
            Column(name="id", type=ColumnType.UUID, nullable=False),
            Column(name="name", type=ColumnType.VARCHAR, nullable=False, length=120),
            Column(name="status", type=ColumnType.ENUM, nullable=False, enum_type_name="product_status"),
            Column(name="category_id", type=ColumnType.UUID, nullable=True),
        ),
        primary_key=PrimaryKey(column_names=("id",), name="pk_product"),
        foreign_keys=(category_fk,),
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_non_discriminator_table_preserves_six_file_order_and_byte_identity_snapshot():
    sources = generate_table_sources(_product_table())

    expected_paths_and_hashes = (
        (
            "src/main/java/com/modelia/generated/domain/Product.java",
            "581c941e3d5f920311112eef40c4747ced01a09395c9593dad2c444479d49a16",
        ),
        (
            "src/main/java/com/modelia/generated/persistence/ProductRepository.java",
            "716f324735a2f72b842bf40dd7d95f5e99fbb399880586ba9c32855d13713f4a",
        ),
        (
            "src/main/java/com/modelia/generated/application/dto/ProductRequestDto.java",
            "62f819a0bef7a00b528f71315bc272ff67f2aceba7f866488ea85a8fb39c5777",
        ),
        (
            "src/main/java/com/modelia/generated/application/dto/ProductResponseDto.java",
            "9570379b822f474c442c6651e36b9123db3369459271d9c6d7118488e94dd0e6",
        ),
        (
            "src/main/java/com/modelia/generated/application/ProductService.java",
            "4437ad3141ec81e113b41fddc19a77123d695da57aa6ac73b42c614284352223",
        ),
        (
            "src/main/java/com/modelia/generated/api/ProductController.java",
            "d99e46bf7629c282de274fda0d3966336506c88a46fa433293e7c11228e1ce04",
        ),
    )

    assert tuple((generated_file.path, _sha256(generated_file.contents)) for generated_file in sources.files) == expected_paths_and_hashes
