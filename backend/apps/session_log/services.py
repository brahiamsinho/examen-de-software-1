"""Recording, listing and exporting the per-diagram session log (issue #17).

Sessions: a session is a period of activity in one diagram. A new one starts
when 30 minutes passed without any entry in that diagram, and sessions are
numbered per diagram. The number is decided when the entry is written, from the
diagram's previous entry, so it needs no timers and no connection tracking.
Two entries written at the very same boundary both open the same new session
number, which is the correct outcome, so no lock is needed.
"""
import csv
import datetime
import io
from collections.abc import Sequence
from uuid import UUID

from django.apps import apps
from django.db.models import Count, Max, Min
from django.http import Http404
from django.utils import timezone

from apps.organizations.models import Organization
from apps.session_log.models import ImmutableLogError, LogEntry, LogKind
from apps.uml_commands import commands

__all__ = [
    "AI_LABEL",
    "ImmutableLogError",
    "LogKind",
    "SESSION_GAP",
    "describe_commands",
    "export_csv",
    "list_entries",
    "list_sessions",
    "record",
    "record_change",
    "serialize_entry",
]

SESSION_GAP = datetime.timedelta(minutes=30)
AI_LABEL = "IA"
SYSTEM_LABEL = "Sistema"
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000
MAX_EXPORT = 5000
_MAX_SUMMARY = 500
_MAX_DESCRIBED_COMMANDS = 50
# A spreadsheet runs a cell that starts with one of these as a formula.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _user_label(user) -> str:
    return user.full_name or user.email


def _require_document(organization: Organization, doc_id: UUID) -> None:
    """The single org+document check (404 for a foreign or missing diagram).
    The model is looked up by name so this app never imports `uml_documents`."""
    document = apps.get_model("uml_documents", "UmlDocument")
    if not document.objects.for_organization(organization).filter(pk=doc_id).exists():
        raise Http404("Document not found")


def record(
    *,
    organization: Organization,
    document_id: UUID,
    kind: str,
    summary: str,
    actor=None,
    is_ai: bool = False,
    data: dict | None = None,
    now: datetime.datetime | None = None,
) -> LogEntry:
    """Appends one entry and assigns its session. Call it inside the same
    transaction as the action it describes, so the two are saved together."""
    now = now or timezone.now()
    previous = (
        LogEntry.objects.for_organization(organization)
        .filter(document_id=document_id)
        .order_by("-id")
        .first()
    )
    if previous is None:
        session = 1
    elif now - previous.created_at >= SESSION_GAP:
        session = previous.session + 1
    else:
        session = previous.session

    if is_ai:
        label = AI_LABEL
    else:
        label = _user_label(actor) if actor is not None else SYSTEM_LABEL
    return LogEntry.objects.for_organization(organization).create(
        organization=organization,
        document_id=document_id,
        session=session,
        kind=kind,
        actor=None if is_ai else actor,
        actor_label=label,
        is_ai=is_ai,
        summary=summary[:_MAX_SUMMARY],
        data=data or {},
        created_at=now,
    )


def _names(model, batch: Sequence) -> dict:
    """id -> name for everything the model has, plus the classes this batch creates."""
    names: dict[str, str] = {}
    for uml_class in model.classes:
        names[uml_class.id] = uml_class.name
        names.update({item.id: item.name for item in uml_class.attributes})
        names.update({item.id: item.name for item in uml_class.operations})
    for command in batch:
        if isinstance(command, commands.AddClass):
            names[command.class_id] = command.name
    return names


def _relationship_label(model, relationship_id, names: dict) -> str | None:
    found = next((item for item in model.relationships if item.id == relationship_id), None)
    if found is None:
        return None
    if found.name:
        return found.name
    return f"{names.get(found.source.class_id, '?')} -> {names.get(found.target.class_id, '?')}"


def describe_commands(batch: Sequence, model_before) -> list[dict]:
    """Each command as `{type, label}`: the command's own name and the name of
    what it touched, looked up in the diagram as it was BEFORE the change so a
    removal still says what it removed. An id it cannot resolve gets no label."""
    names = _names(model_before, batch)
    described = []
    for command in batch:
        label: str | None
        if isinstance(command, commands.AddClass):
            label = command.name
        elif isinstance(command, commands.RenameClass):
            label = command.new_name
        elif isinstance(command, commands.RemoveClass):
            label = names.get(command.class_id)
        elif isinstance(command, commands.AddAttribute):
            label = command.attribute.name
        elif isinstance(command, commands.AddOperation):
            label = command.operation.name
        elif isinstance(command, commands.RemoveAttribute):
            label = names.get(command.attribute_id)
        elif isinstance(command, commands.RemoveOperation):
            label = names.get(command.operation_id)
        elif isinstance(command, commands.AddRelationship):
            relationship = command.relationship
            label = relationship.name or (
                f"{names.get(relationship.source.class_id, '?')} -> {names.get(relationship.target.class_id, '?')}"
            )
        elif isinstance(command, (commands.RemoveRelationship, commands.UpdateRelationship)):
            label = _relationship_label(model_before, command.relationship_id, names)
        elif isinstance(command, commands.SetGenerationProfile):
            label = names.get(command.element_id)
        else:
            label = None
        described.append({"type": type(command).__name__, "label": label})
    return described


def record_change(
    *,
    organization: Organization,
    document_id: UUID,
    batch: Sequence,
    model_before,
    revision: int,
    actor=None,
    now: datetime.datetime | None = None,
) -> LogEntry:
    """One entry for one applied command batch."""
    described = describe_commands(batch, model_before)
    summary = "; ".join(f"{item['type']} {item['label']}" if item["label"] else item["type"] for item in described)
    return record(
        organization=organization,
        document_id=document_id,
        kind=LogKind.CHANGE,
        summary=summary,
        actor=actor,
        data={
            "commands": described[:_MAX_DESCRIBED_COMMANDS],
            "total": len(described),
            "revision": revision,
        },
        now=now,
    )


def _filtered(
    organization: Organization,
    doc_id: UUID,
    *,
    session: int | None = None,
    user: str | None = None,
    kind: str | None = None,
):
    _require_document(organization, doc_id)
    entries = LogEntry.objects.for_organization(organization).filter(document_id=doc_id)
    if session is not None:
        entries = entries.filter(session=session)
    if kind:
        entries = entries.filter(kind=kind)
    if user == "ai":
        entries = entries.filter(is_ai=True)
    elif user:
        try:
            UUID(user)
        except ValueError:
            return entries.none()
        entries = entries.filter(actor_id=user)
    return entries


def list_entries(
    *,
    organization: Organization,
    doc_id: UUID,
    session: int | None = None,
    user: str | None = None,
    kind: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[LogEntry]:
    """The latest `limit` matching entries, oldest first. `user` is a user id or
    `"ai"`; a value that is not an id matches nothing."""
    entries = _filtered(organization, doc_id, session=session, user=user, kind=kind)
    latest = entries.order_by("-id")[: max(1, min(limit, MAX_EXPORT))]
    return list(reversed(list(latest)))


def list_sessions(*, organization: Organization, doc_id: UUID) -> list[dict]:
    """Each session with its period, its size and the people who took part."""
    _require_document(organization, doc_id)
    entries = LogEntry.objects.for_organization(organization).filter(document_id=doc_id)
    periods = (
        entries.values("session")
        .annotate(started=Min("created_at"), ended=Max("created_at"), total=Count("id"))
        .order_by("session")
    )
    actors: dict[int, list[dict]] = {}
    seen: set[tuple] = set()
    for row in entries.values("session", "actor_id", "actor_label", "is_ai").order_by("session", "id"):
        who = "ai" if row["is_ai"] else (str(row["actor_id"]) if row["actor_id"] else row["actor_label"])
        if (row["session"], who) in seen:
            continue
        seen.add((row["session"], who))
        actors.setdefault(row["session"], []).append(
            {
                "id": str(row["actor_id"]) if row["actor_id"] else None,
                "label": row["actor_label"],
                "is_ai": row["is_ai"],
            }
        )
    return [
        {
            "session": period["session"],
            "started_at": period["started"].isoformat(),
            "ended_at": period["ended"].isoformat(),
            "entries": period["total"],
            "actors": actors.get(period["session"], []),
        }
        for period in periods
    ]


def serialize_entry(entry: LogEntry) -> dict:
    return {
        "id": str(entry.id),
        "session": entry.session,
        "kind": entry.kind,
        "author": entry.actor_label,
        "author_id": str(entry.actor_id) if entry.actor_id else None,
        "is_ai": entry.is_ai,
        "summary": entry.summary,
        "data": entry.data,
        "created_at": entry.created_at.isoformat(),
    }


def _safe_cell(value: str) -> str:
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def export_csv(entries: Sequence[LogEntry]) -> str:
    """The entries as CSV. Text that a spreadsheet would run as a formula is
    prefixed with a quote, because chat text is typed by users."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "session", "time", "kind", "author", "is_ai", "summary"])
    for entry in entries:
        writer.writerow(
            [
                entry.id,
                entry.session,
                entry.created_at.isoformat(),
                _safe_cell(entry.kind),
                _safe_cell(entry.actor_label),
                "true" if entry.is_ai else "false",
                _safe_cell(entry.summary),
            ]
        )
    return buffer.getvalue()
