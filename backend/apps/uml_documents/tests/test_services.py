"""Service-layer contract: creation, read, command->domain mapping, and
command submission (design.md's Data Flow; spec's Document Creation,
Document Read, Command Submission requirements).
"""
import datetime
import threading
import time
from unittest import mock

import pytest
from django.db import connection, transaction
from django.db.transaction import TransactionManagementError
from django.http import Http404

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_commands import commands
from apps.uml_documents import schemas, services
from apps.uml_documents.errors import InvalidCommandPayloadError
from apps.uml_modeling.domain.elements import (
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlOperation,
    Visibility,
)
from apps.uml_modeling.documents import Position
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity, PrimitiveType
from apps.uml_modeling.validation.diagnostics import DiagnosticCode

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
_LATER = datetime.datetime(2026, 1, 1, 0, 5, tzinfo=datetime.timezone.utc)


@pytest.mark.django_db
def test_create_document():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()

    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    assert document.owner_id == str(owner.id)
    assert document.revision == 1
    assert document.model == CanonicalUmlModel()
    assert document.layout.positions == {}
    assert document.metadata.name == "My Diagram"


@pytest.mark.django_db
def test_get_document():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    other_organization, *_rest = make_org_with_roles()

    created = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    fetched = services.get_document(organization=organization, doc_id=created.id)
    assert fetched == created

    with pytest.raises(Http404):
        services.get_document(organization=other_organization, doc_id=created.id)


@pytest.mark.django_db
def test_list_documents_returns_only_that_org_rows_newest_updated_first():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    other_organization, other_owner, *_rest = make_org_with_roles()

    first = services.create_document(
        organization=organization, owner_id=str(owner.id), name="First", now=_NOW
    )
    third = services.create_document(
        organization=organization,
        owner_id=str(owner.id),
        name="Third",
        now=_NOW + datetime.timedelta(minutes=10),
    )
    second = services.create_document(
        organization=organization,
        owner_id=str(owner.id),
        name="Second",
        now=_LATER,
    )
    services.create_document(
        organization=other_organization, owner_id=str(other_owner.id), name="Other org", now=_NOW
    )

    documents = services.list_documents(organization=organization)

    assert [document.id for document in documents] == [third.id, second.id, first.id]


@pytest.mark.django_db
def test_list_documents_returns_empty_list_for_organization_with_no_documents():
    organization, *_rest = make_org_with_roles()

    documents = services.list_documents(organization=organization)

    assert documents == []


@pytest.mark.django_db
def test_command_from_payload():
    class_id = new_id()
    attribute_id = new_id()
    relationship_id = new_id()
    target_class_id = new_id()

    add_class = services.command_from_payload(
        schemas.AddClassIn(type="AddClass", class_id=class_id, name="Order")
    )
    assert add_class == commands.AddClass(class_id=class_id, name="Order")

    remove_class = services.command_from_payload(
        schemas.RemoveClassIn(type="RemoveClass", class_id=class_id)
    )
    assert remove_class == commands.RemoveClass(class_id=class_id)

    rename_class = services.command_from_payload(
        schemas.RenameClassIn(type="RenameClass", class_id=class_id, new_name="Renamed")
    )
    assert rename_class == commands.RenameClass(class_id=class_id, new_name="Renamed")

    add_attribute = services.command_from_payload(
        schemas.AddAttributeIn(
            type="AddAttribute",
            class_id=class_id,
            attribute=schemas.UmlAttributeIn(
                id=attribute_id, name="reference", type="String", visibility="private"
            ),
        )
    )
    assert add_attribute == commands.AddAttribute(
        class_id=class_id,
        attribute=UmlAttribute(
            id=attribute_id, name="reference", type=PrimitiveType.STRING, visibility=Visibility.PRIVATE
        ),
    )

    remove_attribute = services.command_from_payload(
        schemas.RemoveAttributeIn(
            type="RemoveAttribute", class_id=class_id, attribute_id=attribute_id
        )
    )
    assert remove_attribute == commands.RemoveAttribute(class_id=class_id, attribute_id=attribute_id)

    operation_id = new_id()
    add_operation = services.command_from_payload(
        schemas.AddOperationIn(
            type="AddOperation",
            class_id=class_id,
            operation=schemas.UmlOperationIn(
                id=operation_id, name="crearUsuario", return_type="String", visibility="public"
            ),
        )
    )
    assert add_operation == commands.AddOperation(
        class_id=class_id,
        operation=UmlOperation(
            id=operation_id,
            name="crearUsuario",
            return_type=PrimitiveType.STRING,
            parameters=(),
            visibility=Visibility.PUBLIC,
        ),
    )

    add_operation_no_return_type_omitted = services.command_from_payload(
        schemas.AddOperationIn(
            type="AddOperation",
            class_id=class_id,
            operation=schemas.UmlOperationIn(id=operation_id, name="guardar"),
        )
    )
    assert add_operation_no_return_type_omitted.operation.return_type is None
    assert add_operation_no_return_type_omitted.operation.parameters == ()

    add_operation_no_return_type_null = services.command_from_payload(
        schemas.AddOperationIn(
            type="AddOperation",
            class_id=class_id,
            operation=schemas.UmlOperationIn(id=operation_id, name="guardar", return_type=None),
        )
    )
    assert add_operation_no_return_type_null.operation.return_type is None

    with pytest.raises(InvalidCommandPayloadError):
        services.command_from_payload(
            schemas.AddOperationIn(
                type="AddOperation",
                class_id=class_id,
                operation=schemas.UmlOperationIn(id=operation_id, name="guardar", return_type=""),
            )
        )

    remove_operation = services.command_from_payload(
        schemas.RemoveOperationIn(
            type="RemoveOperation", class_id=class_id, operation_id=operation_id
        )
    )
    assert remove_operation == commands.RemoveOperation(class_id=class_id, operation_id=operation_id)

    add_relationship = services.command_from_payload(
        schemas.AddRelationshipIn(
            type="AddRelationship",
            relationship=schemas.RelationshipIn(
                id=relationship_id,
                kind="association",
                source=schemas.RelationshipEndIn(class_id=class_id, multiplicity="1"),
                target=schemas.RelationshipEndIn(class_id=target_class_id, multiplicity="0..*"),
            ),
        )
    )
    assert add_relationship == commands.AddRelationship(
        relationship=Relationship(
            id=relationship_id,
            kind=RelationshipKind.ASSOCIATION,
            source=RelationshipEnd(class_id=class_id, multiplicity=Multiplicity(1, 1)),
            target=RelationshipEnd(class_id=target_class_id, multiplicity=Multiplicity(0, None)),
        )
    )

    remove_relationship = services.command_from_payload(
        schemas.RemoveRelationshipIn(type="RemoveRelationship", relationship_id=relationship_id)
    )
    assert remove_relationship == commands.RemoveRelationship(relationship_id=relationship_id)


@pytest.mark.django_db
def test_submit_command():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    class_id = new_id()
    result_1 = services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_id, name="Order"),
        now=_NOW,
    )
    assert result_1.document.revision == document.revision + 1

    attribute_id = new_id()
    attribute = UmlAttribute(id=attribute_id, name="reference", type=PrimitiveType.STRING)
    result_2 = services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddAttribute(class_id=class_id, attribute=attribute),
        now=_LATER,
    )
    assert result_2.document.revision == result_1.document.revision + 1

    persisted = services.get_document(organization=organization, doc_id=document.id)
    assert persisted.revision == result_2.document.revision
    persisted_class = persisted.model.class_by_id(class_id)
    assert persisted_class is not None
    assert len(persisted_class.attributes) == 1


@pytest.mark.django_db
def test_submit_command_persists_invalid_result_with_diagnostics():
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="My Diagram", now=_NOW
    )

    class_a_id = new_id()
    services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_a_id, name="A"),
        now=_NOW,
    )

    relationship = Relationship(
        id=new_id(),
        kind=RelationshipKind.ASSOCIATION,
        source=RelationshipEnd(class_id=class_a_id, multiplicity=Multiplicity(1, 1)),
        target=RelationshipEnd(class_id=new_id(), multiplicity=Multiplicity(1, 1)),
    )

    result = services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddRelationship(relationship=relationship),
        now=_LATER,
    )

    assert result.validation_result.is_blocking
    codes = {diagnostic.code for diagnostic in result.validation_result.diagnostics}
    assert DiagnosticCode.INVALID_RELATIONSHIP_ENDPOINT in codes

    persisted = services.get_document(organization=organization, doc_id=document.id)
    assert persisted.revision == result.document.revision
    assert len(persisted.model.relationships) == 1


# --- DD1: locked row read (design.md DD1, tasks 2.1/2.2) --------------------


@pytest.mark.django_db(transaction=True)
def test_get_row_for_update_outside_transaction_raises_transaction_management_error():
    """`select_for_update()` is only legal inside a transaction. `_get_row`
    also backs `get_document`'s non-transactional GET view, so calling it
    with `for_update=True` outside any transaction must raise rather than
    silently locking nothing.
    """
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Locked", now=_NOW
    )

    with pytest.raises(TransactionManagementError):
        services._get_row(organization=organization, doc_id=document.id, for_update=True)


@pytest.mark.django_db
def test_get_row_for_update_inside_submit_command_does_not_raise():
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Locked", now=_NOW
    )

    result = services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=new_id(), name="Locked"),
        now=_NOW,
    )

    assert result.document.revision == document.revision + 1


@pytest.mark.django_db(transaction=True)
def test_get_row_for_update_still_enforces_tenant_scoping():
    """The lock never bypasses `for_organization` — org B's lookup on org
    A's `doc_id` still 404s, because `.select_for_update()` chains AFTER
    the tenant filter, not instead of it.
    """
    organization, owner, *_rest = make_org_with_roles()
    other_organization, *_rest_other = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Locked", now=_NOW
    )

    with transaction.atomic():
        with pytest.raises(Http404):
            services._get_row(organization=other_organization, doc_id=document.id, for_update=True)


# --- DD2/DD7: broadcast after commit (design.md DD2, task 2.6) -------------
# `transaction.on_commit` callbacks never fire under the default
# `pytest.mark.django_db` wrapper — `django_capture_on_commit_callbacks` (or
# `transaction=True`) is required, per this cycle's testing gotcha.


@pytest.mark.django_db
def test_submit_command_broadcasts_exactly_once_after_commit(django_capture_on_commit_callbacks):
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Broadcast", now=_NOW
    )

    with mock.patch("apps.uml_documents.services.broadcast_document") as mock_broadcast:
        with django_capture_on_commit_callbacks(execute=True):
            result = services.submit_command(
                organization=organization,
                doc_id=document.id,
                command=commands.AddClass(class_id=new_id(), name="Order"),
                now=_NOW,
            )

    mock_broadcast.assert_called_once_with(document=result.document)


@pytest.mark.django_db
def test_submit_command_does_not_broadcast_when_apply_raises(django_capture_on_commit_callbacks):
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Broadcast", now=_NOW
    )

    with mock.patch("apps.uml_documents.services.apply", side_effect=RuntimeError("boom")):
        with mock.patch("apps.uml_documents.services.broadcast_document") as mock_broadcast:
            with django_capture_on_commit_callbacks(execute=True):
                with pytest.raises(RuntimeError):
                    services.submit_command(
                        organization=organization,
                        doc_id=document.id,
                        command=commands.AddClass(class_id=new_id(), name="Order"),
                        now=_NOW,
                    )

    mock_broadcast.assert_not_called()


# --- DD1: concurrent submissions, no lost update (task 2.8) -----------------


@pytest.mark.django_db(transaction=True)
def test_submit_command_concurrent_calls_do_not_lose_updates():
    """Two concurrent `submit_command` calls on one document both persist;
    the final `revision` is exactly `n + 2` — the row lock (DD1) serializes
    the second call behind the first's commit instead of both reading the
    same starting revision and one write clobbering the other.
    """
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Concurrent", now=_NOW
    )
    start_revision = document.revision

    a_holds_lock = threading.Event()
    b_attempted = threading.Event()
    release_a = threading.Event()
    real_apply = services.apply

    def instrumented_apply(document_, command_, *, now):
        # Only the first call through (thread A, which got the lock first)
        # pauses here — it deliberately holds the row lock open until
        # thread B has had a chance to block on it.
        if not a_holds_lock.is_set():
            a_holds_lock.set()
            b_attempted.wait(timeout=2)
            release_a.wait(timeout=2)
        return real_apply(document_, command_, now=now)

    results: dict[str, object] = {}
    errors: list[Exception] = []

    def run(label: str, class_name: str) -> None:
        try:
            results[label] = services.submit_command(
                organization=organization,
                doc_id=document.id,
                command=commands.AddClass(class_id=new_id(), name=class_name),
                now=_NOW,
            )
        except Exception as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)
        finally:
            connection.close()

    # This test's subject is DD1 (locking), not DD2 (broadcast) — the
    # broadcast fan-out is covered separately by
    # test_submit_command_broadcasts_exactly_once_after_commit and has its
    # own Redis-backed channel layer dependency, orthogonal to row locking.
    with (
        mock.patch("apps.uml_documents.services.apply", side_effect=instrumented_apply),
        mock.patch("apps.uml_documents.services.broadcast_document"),
    ):
        thread_a = threading.Thread(target=run, args=("a", "A"))
        thread_b = threading.Thread(target=run, args=("b", "B"))
        thread_a.start()
        assert a_holds_lock.wait(timeout=2)
        thread_b.start()
        # Give thread B a moment to reach `_get_row(for_update=True)` and
        # actually block on Postgres' row lock before releasing thread A.
        time.sleep(0.2)
        b_attempted.set()
        release_a.set()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)

    assert errors == []
    final = services.get_document(organization=organization, doc_id=document.id)
    assert final.revision == start_revision + 2


# --- DD8: layout persistence via non-command path (design.md DD8, tasks 2.1/2.2) --


@pytest.mark.django_db
def test_save_layout_position_bumps_revision_by_one_and_leaves_model_unchanged():
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Layout", now=_NOW
    )
    class_id = new_id()
    services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_id, name="Order"),
        now=_NOW,
    )
    before = services.get_document(organization=organization, doc_id=document.id)

    updated = services.save_layout_position(
        organization=organization,
        doc_id=document.id,
        class_id=str(class_id),
        position=Position(x=10.0, y=20.0),
        now=_LATER,
    )

    assert updated.revision == before.revision + 1
    assert updated.model == before.model
    assert updated.layout.positions[class_id] == Position(x=10.0, y=20.0)

    persisted = services.get_document(organization=organization, doc_id=document.id)
    assert persisted.revision == updated.revision
    assert persisted.layout.positions[class_id] == Position(x=10.0, y=20.0)


@pytest.mark.django_db
def test_save_layout_position_for_absent_class_id_writes_nothing_and_does_not_bump_revision():
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Layout", now=_NOW
    )
    before = services.get_document(organization=organization, doc_id=document.id)

    updated = services.save_layout_position(
        organization=organization,
        doc_id=document.id,
        class_id="does-not-exist",
        position=Position(x=1.0, y=2.0),
        now=_LATER,
    )

    assert updated.revision == before.revision
    assert updated.layout.positions == before.layout.positions

    persisted = services.get_document(organization=organization, doc_id=document.id)
    assert persisted.revision == before.revision
    assert persisted.layout.positions == before.layout.positions


@pytest.mark.django_db
def test_save_layout_position_prunes_a_stale_entry_for_a_removed_class_on_next_persist():
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Layout", now=_NOW
    )
    class_a = new_id()
    class_b = new_id()
    services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_a, name="A"),
        now=_NOW,
    )
    services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_b, name="B"),
        now=_NOW,
    )
    services.save_layout_position(
        organization=organization,
        doc_id=document.id,
        class_id=str(class_a),
        position=Position(x=1.0, y=1.0),
        now=_NOW,
    )
    services.save_layout_position(
        organization=organization,
        doc_id=document.id,
        class_id=str(class_b),
        position=Position(x=2.0, y=2.0),
        now=_NOW,
    )
    services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.RemoveClass(class_id=class_a),
        now=_LATER,
    )

    updated = services.save_layout_position(
        organization=organization,
        doc_id=document.id,
        class_id=str(class_b),
        position=Position(x=3.0, y=3.0),
        now=_LATER,
    )

    assert class_a not in updated.layout.positions
    assert updated.layout.positions[class_b] == Position(x=3.0, y=3.0)


@pytest.mark.django_db
def test_save_layout_position_broadcasts_exactly_once_after_commit(django_capture_on_commit_callbacks):
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Layout", now=_NOW
    )
    class_id = new_id()
    services.submit_command(
        organization=organization,
        doc_id=document.id,
        command=commands.AddClass(class_id=class_id, name="Order"),
        now=_NOW,
    )

    with mock.patch("apps.uml_documents.services.broadcast_document") as mock_broadcast:
        with django_capture_on_commit_callbacks(execute=True):
            updated = services.save_layout_position(
                organization=organization,
                doc_id=document.id,
                class_id=str(class_id),
                position=Position(x=5.0, y=5.0),
                now=_LATER,
            )

    mock_broadcast.assert_called_once_with(document=updated)
