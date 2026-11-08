"""Read-only HTTP adapter for deterministic architecture audit reports."""
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Path, Router
from ninja.security import django_auth

from apps.architecture_audit.analyzer import report
from apps.architecture_audit.exports import markdown
from apps.organizations.permissions import resolve_membership
from apps.uml_documents import services

architecture_audit_router = Router(auth=django_auth)


def _report(request: HttpRequest, org_slug: str, doc_id: UUID) -> dict:
    membership = resolve_membership(request, org_slug)  # every authorized member may read
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    return report(document.model, document_id=str(document.id), revision=document.revision)


@architecture_audit_router.get("/{doc_id}/architecture-audit")
def architecture_audit_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    """Analyze the current canonical model in memory without modifying it."""
    return _report(request, org_slug, doc_id)


@architecture_audit_router.get("/{doc_id}/architecture-audit/export")
def architecture_audit_export_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, format: str = "json"):
    audit_report = _report(request, org_slug, doc_id)
    if format == "markdown":
        response = HttpResponse(markdown(audit_report), content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="architecture-audit-{doc_id}.md"'
        return response
    if format == "json":
        import json

        response = HttpResponse(
            json.dumps(audit_report, ensure_ascii=True, indent=2) + "\n",
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="architecture-audit-{doc_id}.json"'
        return response
    return HttpResponse("Unsupported format", status=400, content_type="text/plain; charset=utf-8")
