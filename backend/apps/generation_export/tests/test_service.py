"""Unit tests for `build_project_archive` (pure: document in, zip bytes out)."""
import datetime
import io
import zipfile
from uuid import uuid4

import pytest

from apps.generation_export.service import (
    FALLBACK_ARCHIVE_NAME,
    NothingToGenerateError,
    build_project_archive,
    slugify_document_name,
)
from apps.relational_mapping.mapping.errors import UnmappableModelError
from apps.relational_mapping.tests.factories import a_class, an_attribute
from apps.spring_generator.emit.errors import UngeneratableSourceError
from apps.uml_modeling.documents import DiagramLayout, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.model import CanonicalUmlModel

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def _document(*, name: str = "Sales Demo", classes=None) -> ProjectDocument:
    if classes is None:
        classes = (a_class(name="Order", attributes=(an_attribute(name="reference"),)),)
    return ProjectDocument(
        id=uuid4(),
        metadata=ProjectMetadata(name=name),
        owner_id="1",
        model=CanonicalUmlModel(classes=tuple(classes)),
        layout=DiagramLayout(),
        created_at=_NOW,
        updated_at=_NOW,
    )


def _names(archive: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        return zf.namelist()


class TestBuildProjectArchive:
    def test_zip_contains_build_files_application_and_entity(self):
        names = _names(build_project_archive(_document()))

        assert "sales-demo/build.gradle" in names
        assert "sales-demo/settings.gradle" in names
        assert any(n.endswith("/Application.java") for n in names)
        assert any(n.endswith("/Order.java") for n in names)

    def test_every_entry_lives_under_the_single_top_folder(self):
        names = _names(build_project_archive(_document()))

        assert names
        assert all(n.startswith("sales-demo/") for n in names)

    def test_bytes_are_deterministic_across_calls(self):
        document = _document()

        assert build_project_archive(document) == build_project_archive(document)

    def test_entry_timestamps_are_fixed(self):
        with zipfile.ZipFile(io.BytesIO(build_project_archive(_document()))) as zf:
            assert {info.date_time for info in zf.infolist()} == {(1980, 1, 1, 0, 0, 0)}

    def test_blank_document_name_falls_back_to_default_folder(self):
        names = _names(build_project_archive(_document(name="   ")))

        assert all(n.startswith(f"{FALLBACK_ARCHIVE_NAME}/") for n in names)

    def test_model_without_classes_raises_nothing_to_generate(self):
        with pytest.raises(NothingToGenerateError):
            build_project_archive(_document(classes=()))

    def test_class_name_without_usable_characters_raises_a_generation_error(self):
        document = _document(classes=(a_class(name="日本"),))

        with pytest.raises((UnmappableModelError, UngeneratableSourceError, ValueError)):
            build_project_archive(document)


class TestSlugifyDocumentName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Sales Demo", "sales-demo"),
            ("  Módulo  Ventas!! ", "modulo-ventas"),
            ("###", FALLBACK_ARCHIVE_NAME),
            ("", FALLBACK_ARCHIVE_NAME),
        ],
    )
    def test_slug(self, raw, expected):
        assert slugify_document_name(raw) == expected
