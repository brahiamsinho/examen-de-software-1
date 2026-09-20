"""Pack the generated Spring Boot backend of a stored document into a zip.

Pipeline: `CanonicalUmlModel` -> `map_to_relational` -> `generate_project_sources`
-> zip. Pure: no database, no filesystem. The archive is byte-deterministic
(generated file order, fixed entry timestamps) so equal documents give equal
downloads.
"""
import io
import re
import unicodedata
import zipfile

from apps.relational_mapping.mapping.mapper import map_to_relational
from apps.spring_generator.emit.renderer import generate_project_sources
from apps.uml_modeling.documents import ProjectDocument

FALLBACK_ARCHIVE_NAME = "modelia-backend"
_BASE_PACKAGE = "com.modelia.generated"
_FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)  # earliest date the zip format allows
_REGULAR_FILE_MODE = 0o644 << 16


class NothingToGenerateError(Exception):
    """The document has no classes, so there is no backend to generate."""


def slugify_document_name(name: str) -> str:
    """ASCII, lowercase, dash-separated; `FALLBACK_ARCHIVE_NAME` if nothing is left."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or FALLBACK_ARCHIVE_NAME


def build_project_archive(document: ProjectDocument) -> bytes:
    if not document.model.classes:
        raise NothingToGenerateError("El documento no tiene clases para generar.")

    sources = generate_project_sources(
        map_to_relational(document.model), base_package=_BASE_PACKAGE
    )
    top_folder = slugify_document_name(document.metadata.name)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for generated_file in sources.files:
            entry = zipfile.ZipInfo(
                f"{top_folder}/{generated_file.path}", date_time=_FIXED_ZIP_TIMESTAMP
            )
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = _REGULAR_FILE_MODE
            archive.writestr(entry, generated_file.contents.encode("utf-8"))
    return buffer.getvalue()
