"""Per-diagram session log (issue #17): who did what, grouped into sessions,
append-only, filterable and exportable."""
import csv
import datetime
import io

import pytest
from django.http import Http404
from django.utils import timezone

from apps.organizations.tests.factories import make_org_with_roles
from apps.session_log import services as log
from apps.session_log.models import LogEntry, LogKind
from apps.uml_documents import schemas, services

_T0 = datetime.datetime(2026, 11, 7, 10, 0, tzinfo=datetime.timezone.utc)


def _minutes(value):
    return _T0 + datetime.timedelta(minutes=value)


def _document(organization, owner, name="Board"):
    return services.create_document(organization=organization, owner_id=str(owner.id), name=name, now=timezone.now())


def _record(organization, document, actor=None, at=0, kind=LogKind.CHANGE, summary="did something", **extra):
    return log.record(
        organization=organization,
        document_id=document.id,
        kind=kind,
        actor=actor,
        summary=summary,
        now=_minutes(at),
        **extra,
    )


def _entries(organization, document, **filters):
    return log.list_entries(organization=organization, doc_id=document.id, **filters)


@pytest.mark.django_db
class TestRecording:
    def test_an_entry_keeps_who_what_and_when(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        entry = _record(organization, document, editor, at=5, summary="Added class", data={"k": 1})

        assert entry.actor_id == editor.id
        assert entry.actor_label == (editor.full_name or editor.email)
        assert entry.is_ai is False
        assert entry.created_at == _minutes(5)
        assert entry.kind == LogKind.CHANGE and entry.summary == "Added class" and entry.data == {"k": 1}

    def test_the_author_name_is_a_snapshot_that_survives_a_rename_and_the_user_being_deleted(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        entry = _record(organization, document, editor)
        original_label = entry.actor_label

        editor.full_name = "Someone Else"
        editor.save()
        editor.delete()

        stored = LogEntry.all_objects.get(pk=entry.pk)
        assert stored.actor_id is None
        assert stored.actor_label == original_label

    def test_the_ai_is_its_own_author(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        entry = _record(organization, document, None, is_ai=True, kind=LogKind.PROPOSAL_CREATED)

        assert entry.is_ai is True and entry.actor_id is None and entry.actor_label == "IA"

    def test_an_entry_without_an_author_is_recorded_as_the_system(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        entry = _record(organization, document, None)

        assert entry.is_ai is False and entry.actor_label == "Sistema"


@pytest.mark.django_db
class TestSessions:
    def test_the_first_entry_opens_session_one_and_activity_keeps_it_open(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        sessions = [_record(organization, document, owner, at=minute).session for minute in (0, 10, 39)]

        assert sessions == [1, 1, 1]

    def test_the_gap_is_measured_from_the_last_entry_not_from_the_start(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        sessions = [_record(organization, document, owner, at=minute).session for minute in range(0, 130, 25)]

        assert set(sessions) == {1}

    def test_thirty_minutes_of_silence_starts_a_new_session(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        first = _record(organization, document, owner, at=0)
        just_inside = _record(organization, document, owner, at=29)
        after_gap = _record(organization, document, owner, at=29 + 30)
        still_in_second = _record(organization, document, owner, at=29 + 30 + 5)
        third = _record(organization, document, owner, at=29 + 30 + 5 + 31)

        assert [first.session, just_inside.session] == [1, 1]
        assert [after_gap.session, still_in_second.session] == [2, 2]
        assert third.session == 3

    def test_each_diagram_numbers_its_own_sessions(self):
        organization, owner, *_ = make_org_with_roles()
        one, two = _document(organization, owner, "One"), _document(organization, owner, "Two")
        _record(organization, one, owner, at=0)
        _record(organization, one, owner, at=100)

        assert _record(organization, two, owner, at=101).session == 1

    def test_the_summary_lists_each_session_with_its_period_size_and_people(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, at=0)
        _record(organization, document, editor, at=5)
        _record(organization, document, None, at=6, is_ai=True)
        _record(organization, document, editor, at=200)

        sessions = log.list_sessions(organization=organization, doc_id=document.id)

        assert [s["session"] for s in sessions] == [1, 2]
        first = sessions[0]
        assert (first["started_at"], first["ended_at"], first["entries"]) == (
            _minutes(0).isoformat(),
            _minutes(6).isoformat(),
            3,
        )
        assert {a["label"] for a in first["actors"]} == {owner.full_name or owner.email, editor.full_name or editor.email, "IA"}
        assert [a["label"] for a in sessions[1]["actors"]] == [editor.full_name or editor.email]


@pytest.mark.django_db
class TestAppendOnly:
    def test_an_existing_entry_cannot_be_saved_again(self):
        organization, owner, *_ = make_org_with_roles()
        entry = _record(organization, _document(organization, owner), owner)

        entry.summary = "edited"
        with pytest.raises(log.ImmutableLogError):
            entry.save()

        assert LogEntry.all_objects.get(pk=entry.pk).summary == "did something"

    def test_an_entry_cannot_be_deleted(self):
        organization, owner, *_ = make_org_with_roles()
        entry = _record(organization, _document(organization, owner), owner)

        with pytest.raises(log.ImmutableLogError):
            entry.delete()

        assert LogEntry.all_objects.filter(pk=entry.pk).exists()

    @pytest.mark.parametrize("manager", ["scoped", "all"])
    def test_a_bulk_update_or_delete_is_refused(self, manager):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner)
        rows = (
            LogEntry.objects.for_organization(organization).filter(document_id=document.id)
            if manager == "scoped"
            else LogEntry.all_objects.filter(document_id=document.id)
        )

        with pytest.raises(log.ImmutableLogError):
            rows.update(summary="rewritten")
        with pytest.raises(log.ImmutableLogError):
            rows.delete()

        assert LogEntry.all_objects.filter(document_id=document.id).count() == 1

    def test_the_author_can_never_be_reassigned_even_though_deleting_an_account_clears_it(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        entry = _record(organization, document, editor)

        with pytest.raises(log.ImmutableLogError):
            LogEntry.all_objects.filter(pk=entry.pk).update(actor=owner)
        with pytest.raises(log.ImmutableLogError):
            LogEntry.all_objects.filter(pk=entry.pk).update(actor=None, summary="rewritten")

        assert LogEntry.all_objects.get(pk=entry.pk).actor_id == editor.id

    def test_deleting_the_diagram_takes_its_log_with_it(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner)

        services.delete_document(organization=organization, doc_id=document.id)

        assert not LogEntry.all_objects.filter(document_id=document.id).exists()


@pytest.mark.django_db
class TestListing:
    def test_entries_come_oldest_first_and_a_limit_keeps_the_latest(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        for minute in range(5):
            _record(organization, document, owner, at=minute, summary=f"s{minute}")

        assert [e.summary for e in _entries(organization, document)] == [f"s{i}" for i in range(5)]
        assert [e.summary for e in _entries(organization, document, limit=2)] == ["s3", "s4"]

    def test_it_filters_by_session(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, at=0, summary="a")
        _record(organization, document, owner, at=100, summary="b")

        assert [e.summary for e in _entries(organization, document, session=2)] == ["b"]

    def test_it_filters_by_user_and_the_ai_counts_as_a_user(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, at=0, summary="owner")
        _record(organization, document, editor, at=1, summary="editor")
        _record(organization, document, None, at=2, is_ai=True, summary="ai")

        assert [e.summary for e in _entries(organization, document, user=str(editor.id))] == ["editor"]
        assert [e.summary for e in _entries(organization, document, user="ai")] == ["ai"]

    def test_a_user_id_that_is_not_an_id_matches_nothing_instead_of_failing(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner)

        assert _entries(organization, document, user="not-a-uuid") == []

    def test_it_filters_by_kind(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, kind=LogKind.CHAT_MESSAGE, summary="chat")
        _record(organization, document, owner, kind=LogKind.CHANGE, summary="change")

        assert [e.summary for e in _entries(organization, document, kind="chat.message")] == ["chat"]

    def test_filters_combine(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, editor, at=0, summary="old editor")
        _record(organization, document, owner, at=100, summary="new owner")
        _record(organization, document, editor, at=101, summary="new editor")

        assert [e.summary for e in _entries(organization, document, session=2, user=str(editor.id))] == ["new editor"]

    def test_another_organizations_diagram_is_not_reachable_and_logs_never_mix(self):
        org_a, owner_a, *_ = make_org_with_roles()
        org_b, owner_b, *_ = make_org_with_roles()
        doc_a, doc_b = _document(org_a, owner_a), _document(org_b, owner_b)
        _record(org_a, doc_a, owner_a, summary="secret of A")

        with pytest.raises(Http404):
            _entries(org_b, doc_a)
        with pytest.raises(Http404):
            log.list_sessions(organization=org_b, doc_id=doc_a.id)
        assert _entries(org_b, doc_b) == []


@pytest.mark.django_db
class TestDescribingChanges:
    def _add_class(self, name, class_id=None):
        return services.command_from_payload(schemas.AddClassIn(type="AddClass", class_id=class_id or f"id-{name}", name=name))

    def test_commands_are_described_by_type_and_name(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        rename = services.command_from_payload(schemas.RenameClassIn(type="RenameClass", class_id="id-A", new_name="B"))

        described = log.describe_commands([self._add_class("A"), rename], document.model)

        assert described == [{"type": "AddClass", "label": "A"}, {"type": "RenameClass", "label": "B"}]

    def test_removing_something_is_described_with_the_name_it_had(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        services.submit_commands(
            organization=organization, doc_id=document.id, commands_to_apply=[self._add_class("Pedido")], now=timezone.now()
        )
        before = services.get_document(organization=organization, doc_id=document.id)
        remove = services.command_from_payload(schemas.RemoveClassIn(type="RemoveClass", class_id="id-Pedido"))

        assert log.describe_commands([remove], before.model) == [{"type": "RemoveClass", "label": "Pedido"}]

    def test_an_unknown_id_is_described_without_a_name_instead_of_failing(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        remove = services.command_from_payload(schemas.RemoveClassIn(type="RemoveClass", class_id="ghost"))

        assert log.describe_commands([remove], document.model) == [{"type": "RemoveClass", "label": None}]


@pytest.mark.django_db
class TestExport:
    def _rows(self, text):
        return list(csv.reader(io.StringIO(text)))

    def test_the_csv_has_one_row_per_entry_with_the_columns_people_need(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, editor, at=3, summary="Added class 'A'")

        rows = self._rows(log.export_csv(_entries(organization, document)))

        assert rows[0] == ["id", "session", "time", "kind", "author", "is_ai", "summary"]
        assert rows[1][1:] == ["1", _minutes(3).isoformat(), "change", editor.full_name or editor.email, "false", "Added class 'A'"]

    def test_text_that_a_spreadsheet_would_run_as_a_formula_is_neutralized(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        for text in ("=HYPERLINK(\"http://x\")", "+1", "-1", "@SUM(A1)", "\tcmd"):
            _record(organization, document, owner, summary=text)

        cells = [row[6] for row in self._rows(log.export_csv(_entries(organization, document)))[1:]]

        assert all(cell.startswith("'") for cell in cells)

    def test_the_csv_respects_the_filters_it_is_given(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _record(organization, document, owner, at=0, summary="owner")
        _record(organization, document, editor, at=1, summary="editor")

        rows = self._rows(log.export_csv(_entries(organization, document, user=str(editor.id))))

        assert [row[6] for row in rows[1:]] == ["editor"]
