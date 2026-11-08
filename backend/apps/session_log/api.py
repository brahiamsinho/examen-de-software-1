"""HTTP router for the per-diagram session log (issue #17). Read-only by
design: there is no endpoint that writes, edits or deletes an entry. Any member
of the organization (a VIEWER included) may read and export it; the shared
`resolve_membership` plus the org+document check answer 404 for anyone else.
"""
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from ninja import Path, Query, Router
from ninja.security import django_auth

from apps.organizations.permissions import resolve_membership
from apps.session_log import services
from apps.session_log.schemas import LogEntryOut, LogSessionOut

log_router = Router(auth=django_auth)


@log_router.get("/{doc_id}/log", response=list[LogEntryOut])
def list_log_view(
    request: HttpRequest,
    org_slug: Path[str],
    doc_id: UUID,
    session: Query[int | None] = None,
    user: Query[str | None] = None,
    kind: Query[str | None] = None,
    limit: Query[int] = services.DEFAULT_LIMIT,
):
    membership = resolve_membership(request, org_slug)  # any member reads
    entries = services.list_entries(
        organization=membership.organization,
        doc_id=doc_id,
        session=session,
        user=user,
        kind=kind,
        limit=min(limit, services.MAX_LIMIT),
    )
    return [services.serialize_entry(entry) for entry in entries]


@log_router.get("/{doc_id}/log/sessions", response=list[LogSessionOut])
def list_log_sessions_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)
    return services.list_sessions(organization=membership.organization, doc_id=doc_id)


@log_router.get("/{doc_id}/log/export")
def export_log_view(
    request: HttpRequest,
    org_slug: Path[str],
    doc_id: UUID,
    session: Query[int | None] = None,
    user: Query[str | None] = None,
    kind: Query[str | None] = None,
):
    """The matching entries as a CSV download (same filters as the listing)."""
    membership = resolve_membership(request, org_slug)
    entries = services.list_entries(
        organization=membership.organization,
        doc_id=doc_id,
        session=session,
        user=user,
        kind=kind,
        limit=services.MAX_EXPORT,
    )
    response = HttpResponse(services.export_csv(entries), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="session-log-{doc_id}.csv"'
    return response
