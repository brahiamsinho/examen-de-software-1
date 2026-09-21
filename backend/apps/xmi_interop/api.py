"""HTTP router for the Enterprise Architect XMI import/export.

Thin, like `apps.generation_export.api`: resolve membership -> check role ->
call the pure importer/exporter -> serialize. Import errors become a stable 422
`{detail, code}` body, caught in the view (no app-wide handler, so unrelated
routers' errors are never swallowed).
"""
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from ninja import File, Path, Router, Status, UploadedFile
from ninja.security import django_auth

from apps.generation_export.service import slugify_document_name
from apps.organizations.constants import Role
from apps.organizations.permissions import require_role, resolve_membership
from apps.uml_documents import codec, services
from apps.uml_documents.errors import DocumentNotEmptyError
from apps.uml_documents.schemas import DocumentOut
from apps.xmi_interop.errors import InvalidXmiError, XmiError
from apps.xmi_interop.exporter import export_xmi
from apps.xmi_interop.importer import MAX_XMI_BYTES, import_xmi

xmi_router = Router(auth=django_auth)

_MAX_NAME_LENGTH = 120


class DocumentImportOut(DocumentOut):
    warnings: list[str]


def _parse_upload(file: UploadedFile):
    """Shared by both import endpoints: size limit + parse (raises `XmiError`)."""
    if file.size is not None and file.size > MAX_XMI_BYTES:
        raise InvalidXmiError("El archivo supera el máximo permitido de 5 MB.")
    return import_xmi(file.read())


@xmi_router.post("/import-xmi", response={201: DocumentImportOut, 422: dict})
def import_xmi_view(request: HttpRequest, org_slug: Path[str], file: File[UploadedFile]):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        result = _parse_upload(file)
    except XmiError as exc:
        return Status(422, {"detail": str(exc), "code": exc.code})

    file_stem = (file.name or "").rsplit(".", 1)[0]
    name = (result.name or file_stem or "Modelo importado")[:_MAX_NAME_LENGTH]
    document = services.create_document_from_model(
        organization=membership.organization,
        owner_id=str(request.user.id),
        name=name,
        model=result.model,
        layout=result.layout,
        now=timezone.now(),
    )
    return Status(201, {**codec.document_out(document), "warnings": list(result.warnings)})


@xmi_router.post(
    "/{doc_id}/import-xmi", response={200: DocumentImportOut, 409: dict, 422: dict}
)
def import_xmi_into_document_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, file: File[UploadedFile]
):
    """Loads the XMI INTO an existing blank document (409 if it already has content)."""
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    services.get_document(organization=membership.organization, doc_id=doc_id)  # 404 first
    try:
        result = _parse_upload(file)
    except XmiError as exc:
        return Status(422, {"detail": str(exc), "code": exc.code})
    try:
        document = services.replace_blank_document_content(
            organization=membership.organization,
            doc_id=doc_id,
            model=result.model,
            layout=result.layout,
            now=timezone.now(),
        )
    except DocumentNotEmptyError:
        return Status(
            409,
            {
                "detail": "Este diagrama ya tiene contenido. Importa en un diagrama en blanco.",
                "code": "document_not_empty",
            },
        )
    return Status(200, {**codec.document_out(document), "warnings": list(result.warnings)})


@xmi_router.get("/{doc_id}/export-xmi", response={200: None})
def export_xmi_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)  # any member reads
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    response = HttpResponse(export_xmi(document), content_type="application/xml")
    filename = f"{slugify_document_name(document.metadata.name)}.xml"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
