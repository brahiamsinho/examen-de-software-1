"""HTTP router for the generated-backend download.

Thin, like `apps.uml_documents.api`: resolve membership -> load the document
-> call one service function -> serialize. Any org member may download (it is
a read); generation failures become a stable 422 JSON body instead of a 500.
Failures are caught in the view, not with app-wide handlers, because a global
`ValueError` handler would swallow unrelated bugs of other routers.
"""
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Path, Router, Status
from ninja.security import django_auth

from apps.generation_export.service import (
    NothingToGenerateError,
    build_project_archive,
    slugify_document_name,
)
from apps.organizations.permissions import resolve_membership
from apps.relational_mapping.mapping.errors import UnmappableModelError
from apps.spring_generator.emit.errors import UngeneratableSourceError
from apps.uml_documents import services

generation_router = Router(auth=django_auth)

GENERATION_ERRORS = (UnmappableModelError, UngeneratableSourceError, ValueError)


def _unprocessable(message: str, code: str) -> Status:
    return Status(422, {"detail": message, "code": code})


@generation_router.get("/{doc_id}/generate", response={200: None, 422: dict})
def generate_backend_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)  # any member reads
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    try:
        archive = build_project_archive(document)
    except NothingToGenerateError as exc:
        return _unprocessable(str(exc), "nothing_to_generate")
    except GENERATION_ERRORS as exc:
        return _unprocessable(str(exc), "generation_failed")

    filename = f"{slugify_document_name(document.metadata.name)}-backend.zip"
    response = HttpResponse(archive, content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
