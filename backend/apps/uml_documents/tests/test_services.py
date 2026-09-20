"""Service-layer contract: creation, read, command->domain mapping, and
command submission (design.md's Data Flow; spec's Document Creation,
Document Read, Command Submission requirements).
"""
import datetime
import threading
import time
import types
from unittest import mock

import pytest
from django.db import connection, transaction
from django.db.transaction import TransactionManagementError
from django.http import Http404

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_commands import commands
from apps.uml_documents import schemas, services
from apps.relational_mapping.mapping.errors import InvalidGenerationProfileError
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


@pytest.mark.parametrize("profile", [{"entity": True, "crud": ["read"]}, {}, None])
def test_command_from_payload_maps_set_generation_profile(profile):
    element_id = new_id()

    command = services.command_from_payload(
        schemas.SetGenerationProfileIn(
            type="SetGenerationProfile", element_id=element_id, profile=profile
        )
    )

    assert command == commands.SetGenerationProfile(element_id=element_id, profile=profile)


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
def test_broadcast_document_sends_a_json_safe_payload_to_the_channel_layer():
    """`channel_layer.group_send` crosses channels_redis' msgpack transport
    in production — a boundary `json.dumps`/`DocumentConsumer.document_update`
    never sees, since that re-serialization only runs after the message has
    already reached the consumer. A raw `uuid.UUID`/`datetime` in the
    message breaks `group_send` itself before any consumer code runs.
    Regression for `id`/`created_at`/`updated_at` silently carrying
    non-JSON-safe Python objects straight from `codec.document_out`.
    """
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Broadcast", now=_NOW
    )

    sent: dict = {}

    async def _fake_group_send(group, message):
        sent["group"] = group
        sent["message"] = message

    fake_channel_layer = mock.Mock()
    fake_channel_layer.group_send = _fake_group_send

    with mock.patch(
        "apps.uml_documents.services.get_channel_layer", return_value=fake_channel_layer
    ):
        services.broadcast_document(document=document)

    payload = sent["message"]["document"]
    assert isinstance(payload["id"], str)
    assert isinstance(payload["created_at"], str)
    assert isinstance(payload["updated_at"], str)


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


# --- DD153-DD157: write-time generation-profile validation ------------------


def _authoring_document():
    """root <- child (GENERALIZATION), plus an unrelated class; one attribute each."""
    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Profiles", now=_NOW
    )
    ids = types.SimpleNamespace(
        doc_id=document.id,
        root=new_id(),
        child=new_id(),
        other=new_id(),
        root_attr=new_id(),
        child_attr=new_id(),
        other_attr=new_id(),
    )

    def attribute(attribute_id, name):
        return UmlAttribute(id=attribute_id, name=name, type=PrimitiveType.STRING)

    generalization = Relationship(
        id=new_id(),
        kind=RelationshipKind.GENERALIZATION,
        source=RelationshipEnd(class_id=ids.child, multiplicity=Multiplicity(1, 1)),
        target=RelationshipEnd(class_id=ids.root, multiplicity=Multiplicity(1, 1)),
    )
    for command in (
        commands.AddClass(class_id=ids.root, name="Vehicle"),
        commands.AddClass(class_id=ids.child, name="Car"),
        commands.AddClass(class_id=ids.other, name="Person"),
        commands.AddAttribute(class_id=ids.root, attribute=attribute(ids.root_attr, "code")),
        commands.AddAttribute(class_id=ids.child, attribute=attribute(ids.child_attr, "doors")),
        commands.AddAttribute(class_id=ids.other, attribute=attribute(ids.other_attr, "name")),
        commands.AddRelationship(relationship=generalization),
    ):
        services.submit_command(
            organization=organization, doc_id=ids.doc_id, command=command, now=_NOW
        )
    return organization, ids


def _set_profile(organization, ids, element_id, profile):
    return services.submit_command(
        organization=organization,
        doc_id=ids.doc_id,
        command=commands.SetGenerationProfile(element_id=element_id, profile=profile),
        now=_LATER,
    )


def _sort_body(attribute_id):
    return {"defaultSort": {"attribute": attribute_id, "direction": "asc"}}


def _assert_no_row_written(organization, ids, revision_before):
    persisted = services.get_document(organization=organization, doc_id=ids.doc_id)
    assert persisted.revision == revision_before
    assert persisted.model.generation_metadata == {}


@pytest.mark.django_db
def test_set_generation_profile_persists_a_valid_table_and_column_profile():
    organization, ids = _authoring_document()

    _set_profile(organization, ids, ids.root, {"entity": True, "crud": ["read", "create"]})
    result = _set_profile(organization, ids, ids.root_attr, {"searchable": True})

    persisted = services.get_document(organization=organization, doc_id=ids.doc_id)
    assert persisted.revision == result.document.revision
    assert persisted.model.generation_metadata == {
        ids.root: {"profile": {"entity": True, "crud": ["read", "create"]}},
        ids.root_attr: {"profile": {"searchable": True}},
    }


@pytest.mark.django_db
@pytest.mark.parametrize("profile", [{"entity": True}, None, {}])
def test_unknown_element_id_is_rejected_even_when_clearing(profile):
    organization, ids = _authoring_document()
    revision = services.get_document(organization=organization, doc_id=ids.doc_id).revision
    unknown = new_id()

    with pytest.raises(InvalidCommandPayloadError) as excinfo:
        _set_profile(organization, ids, unknown, profile)

    assert str(excinfo.value) == (
        f"Unknown element id {unknown!r}: not a class or attribute of this document"
    )
    _assert_no_row_written(organization, ids, revision)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("target", "body", "reason", "key"),
    [
        ("root", {"bogus": True}, "unknown table-level profile key", "bogus"),
        ("root", {"entity": "yes"}, "expected a boolean", "entity"),
        ("root", {"crud": ["create", "fly"]}, "unknown CRUD operation 'fly'", "crud"),
        ("root", {"crud": ["read", "read"]}, "duplicate CRUD operation 'read'", "crud"),
        (
            "root",
            {"defaultSort": {"attribute": "x", "direction": "up"}},
            "expected 'asc' or 'desc'",
            "defaultSort.direction",
        ),
        ("root_attr", {"bogus": True}, "unknown column-level profile key", "bogus"),
        ("root", {"searchable": True}, "unknown table-level profile key", "searchable"),
        ("root_attr", {"entity": True}, "unknown column-level profile key", "entity"),
    ],
)
def test_parser_rejections_surface_with_the_parser_message_verbatim(target, body, reason, key):
    organization, ids = _authoring_document()
    revision = services.get_document(organization=organization, doc_id=ids.doc_id).revision
    element_id = getattr(ids, target)

    with pytest.raises(InvalidCommandPayloadError) as excinfo:
        _set_profile(organization, ids, element_id, body)

    assert str(excinfo.value) == str(InvalidGenerationProfileError(element_id, reason, key=key))
    _assert_no_row_written(organization, ids, revision)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("target", "sort_attribute"),
    [
        ("root", "root_attr"),  # own attribute
        ("root", "child_attr"),  # inheritance root -> descendant attribute (DD157)
        ("child", "child_attr"),  # non-root -> own attribute
        ("other", "other_attr"),  # root without descendants -> own attribute
    ],
)
def test_default_sort_resolves_against_own_and_root_descendant_attributes(target, sort_attribute):
    organization, ids = _authoring_document()

    _set_profile(organization, ids, getattr(ids, target), _sort_body(getattr(ids, sort_attribute)))

    persisted = services.get_document(organization=organization, doc_id=ids.doc_id)
    stored = persisted.model.generation_metadata[getattr(ids, target)]["profile"]
    assert stored == _sort_body(getattr(ids, sort_attribute))


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("target", "sort_attribute", "scope"),
    [
        ("child", "root_attr", "this class"),  # non-root cannot sort by its parent's attribute
        ("other", "root_attr", "this class"),  # root with no descendants, unrelated attribute
        ("root", "other_attr", "this class or its descendants"),  # root with descendants
    ],
)
def test_default_sort_rejects_attributes_outside_the_allowed_set(target, sort_attribute, scope):
    organization, ids = _authoring_document()
    revision = services.get_document(organization=organization, doc_id=ids.doc_id).revision
    element_id = getattr(ids, target)
    attribute_id = getattr(ids, sort_attribute)

    with pytest.raises(InvalidCommandPayloadError) as excinfo:
        _set_profile(organization, ids, element_id, _sort_body(attribute_id))

    assert str(excinfo.value) == (
        f"Invalid generation profile for element {element_id!r}, "
        f"key 'defaultSort.attribute': {attribute_id!r} is not an attribute of {scope}"
    )
    _assert_no_row_written(organization, ids, revision)


@pytest.mark.django_db
def test_clearing_a_known_element_needs_no_parse_and_succeeds():
    organization, ids = _authoring_document()
    _set_profile(organization, ids, ids.root, {"entity": True})

    _set_profile(organization, ids, ids.root, None)

    persisted = services.get_document(organization=organization, doc_id=ids.doc_id)
    assert persisted.model.generation_metadata == {}


@pytest.mark.django_db
def test_a_rejected_profile_is_validated_before_apply_runs():
    organization, ids = _authoring_document()

    with mock.patch.object(services, "apply", wraps=services.apply) as spy:
        with pytest.raises(InvalidCommandPayloadError):
            _set_profile(organization, ids, ids.root, {"bogus": True})

    spy.assert_not_called()
