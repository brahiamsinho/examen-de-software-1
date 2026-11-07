"""Group chat per diagram with one AI model (issue #16). The LLM is injected at
the one seam `chat.py` reads it from; everything else runs for real."""
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

import pytest
from django.db import connection
from django.http import Http404
from django.utils import timezone

from apps.ai_assistant import chat, proposals
from apps.ai_assistant.errors import GeminiRequestError
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import schemas, services


class _Model:
    """Records what the model was sent and answers with a canned chat reply."""

    def __init__(self, reply="Claro, lo reviso.", calls=None, error=None):
        self.requests = []
        self._calls = calls if calls is not None else [GeminiFunctionCall(name="reply_in_chat", args={"message": reply})]
        self._error = error

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        self.requests.append({"system": system_instruction, "transcript": transcript, "tools": [t["name"] for t in tools]})
        if self._error:
            raise self._error
        return self._calls


def _document(organization, owner):
    return services.create_document(organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now())


def _label(user):
    return user.full_name or user.email


def _post(organization, document, author, content, model=None):
    return chat.post_message(
        organization=organization, doc_id=document.id, author=author, content=content, gemini=model or _Model()
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ("@IA hola", True),
        ("hola @ia", True),
        ("hey,@IA!", True),
        ("a@ia.com", False),
        ("@IAmigos", False),
        ("@IAñ", False),
        ("ñ@IA", False),
        ("@IA1", False),
        ("hey_@IA", False),
    ],
)
def test_mention_detection_boundaries(text, expected):
    # The frontend's `mentionsAi` must agree on every one of these.
    assert chat.mentions_ai(text) is expected


@pytest.mark.django_db
class TestPostingMessages:
    def test_a_message_is_stored_with_its_author_and_the_model_stays_silent_without_a_mention(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        model = _Model()

        result = _post(organization, document, editor, "¿Quién toma Pedido?", model)

        assert result.message.content == "¿Quién toma Pedido?"
        assert chat.serialize_message(result.message)["author"] == _label(editor)
        assert chat.serialize_message(result.message)["is_ai"] is False
        assert result.reply is None and model.requests == []

    @pytest.mark.parametrize("text", ["@IA qué falta", "hola @ia, ayuda", "Ayuda @IA"])
    def test_mentioning_the_ai_makes_it_answer_as_one_more_participant(self, text):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        result = _post(organization, document, editor, text, _Model(reply="Falta la clase Cliente."))

        reply = chat.serialize_message(result.reply)
        assert reply["is_ai"] is True and reply["author"] == "IA"
        assert reply["content"] == "Falta la clase Cliente."
        assert [m.content for m in chat.list_messages(organization=organization, doc_id=document.id)] == [
            text,
            "Falta la clase Cliente.",
        ]

    @pytest.mark.parametrize("text", ["escríbeme a hola@ia.com", "@IAmigos qué tal", "la IA sola"])
    def test_text_that_only_looks_like_a_mention_does_not_wake_the_model(self, text):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        model = _Model()

        result = _post(organization, document, editor, text, model)

        assert result.reply is None and model.requests == []

    def test_the_model_receives_everyones_messages_with_their_author_in_order(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _post(organization, document, owner, "Necesitamos un módulo de pedidos")
        _post(organization, document, editor, "Yo hago Cliente")
        model = _Model()

        _post(organization, document, owner, "@IA ¿qué clases faltan?", model)

        transcript = model.requests[0]["transcript"]
        lines = [
            f"{_label(owner)}: Necesitamos un módulo de pedidos",
            f"{_label(editor)}: Yo hago Cliente",
            f"{_label(owner)}: @IA ¿qué clases faltan?",
        ]
        positions = [transcript.index(line) for line in lines]
        assert positions == sorted(positions)
        assert model.requests[0]["tools"] == ["reply_in_chat", "suggest_uml_additions"]

    def test_the_model_also_sees_what_the_ai_said_earlier_and_the_diagram(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        _post(organization, document, owner, "@IA hola", _Model(reply="Hola equipo"))
        model = _Model()

        _post(organization, document, editor, "@IA gracias", model)

        assert "IA: Hola equipo" in model.requests[0]["transcript"]
        assert "Board" in model.requests[0]["transcript"] or "class" in model.requests[0]["transcript"].lower()

    def test_only_the_most_recent_messages_reach_the_model(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        for index in range(chat.CONTEXT_MESSAGES + 10):
            _post(organization, document, owner, f"mensaje-{index}")
        model = _Model()

        _post(organization, document, editor, "@IA resume", model)

        transcript = model.requests[0]["transcript"]
        assert "mensaje-0\n" not in transcript and "mensaje-9\n" not in transcript
        assert f"mensaje-{chat.CONTEXT_MESSAGES + 9}" in transcript

    @pytest.mark.parametrize("content", ["", "   ", "\n"])
    def test_a_blank_message_is_refused(self, content):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with pytest.raises(chat.InvalidMessageError):
            _post(organization, document, editor, content)

        assert chat.list_messages(organization=organization, doc_id=document.id) == []

    def test_a_message_over_the_limit_is_refused(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with pytest.raises(chat.InvalidMessageError):
            _post(organization, document, editor, "x" * (chat.MAX_MESSAGE_LENGTH + 1))

    def test_if_the_model_fails_the_humans_message_is_still_kept(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        result = _post(organization, document, editor, "@IA ayuda", _Model(error=GeminiRequestError("boom")))

        assert result.reply is None and result.ai_error
        assert [m.content for m in chat.list_messages(organization=organization, doc_id=document.id)] == ["@IA ayuda"]

    def test_if_the_model_has_nothing_to_say_nothing_is_posted_in_its_name(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        result = _post(organization, document, editor, "@IA ayuda", _Model(calls=[]))

        assert result.reply is None and result.ai_error is None


def _suggest(classes, reply=None, relationships=()):
    calls = [
        GeminiFunctionCall(
            name="suggest_uml_additions", args={"classes": list(classes), "relationships": list(relationships)}
        )
    ]
    if reply:
        calls.insert(0, GeminiFunctionCall(name="reply_in_chat", args={"message": reply}))
    return _Model(calls=calls)


@pytest.mark.django_db
class TestTheAiSuggestsChangesFromTheChat:
    def test_a_change_the_ai_wants_to_make_becomes_a_pending_draft_and_never_touches_the_diagram(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        model = _suggest(
            [{"name": "Rol", "attributes": [{"name": "nombre", "type": "String"}], "operations": []}],
            reply="Dejé el borrador de Rol.",
        )

        result = _post(organization, document, editor, "@IA agrega la tabla Rol", model)

        assert result.proposal is not None and result.proposal.status == "pending"
        assert result.proposal.requested_by_id == editor.id
        assert result.proposal.prompt == "@IA agrega la tabla Rol"
        assert [c["name"] for c in result.proposal.calls] == ["add_class", "add_attribute"]
        pending = proposals.list_proposals(organization=organization, doc_id=document.id)
        assert [p.id for p in pending] == [result.proposal.id]
        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision and after.model.classes == ()
        assert result.reply.content == "Dejé el borrador de Rol."

    def test_the_draft_is_broadcast_to_the_board(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with mock.patch("apps.ai_assistant.proposals.services.broadcast_event") as broadcast:
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr("django.db.transaction.on_commit", lambda fn: fn())
                _post(organization, document, editor, "@IA agrega Rol", _suggest([{"name": "Rol"}], reply="ok"))

        types = [c.kwargs["payload"]["type"] for c in broadcast.call_args_list]
        assert types.count("proposal.update") == 1
        assert types.count("chat.message") == 2  # the person's message and the AI's reply

    def test_if_the_ai_suggests_without_saying_anything_the_chat_still_tells_the_team(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        result = _post(organization, document, editor, "@IA agrega Rol", _suggest([{"name": "Rol"}]))

        assert result.proposal is not None
        assert result.reply is not None and "pizarra" in result.reply.content

    def test_a_suggestion_that_only_repeats_the_diagram_creates_no_draft(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        services.submit_commands(
            organization=organization,
            doc_id=document.id,
            commands_to_apply=[
                services.command_from_payload(schemas.AddClassIn(type="AddClass", class_id="id-Rol", name="Rol"))
            ],
            now=timezone.now(),
        )

        result = _post(organization, document, editor, "@IA agrega Rol", _suggest([{"name": "rol"}], reply="Ya existe."))

        assert result.proposal is None
        assert proposals.list_proposals(organization=organization, doc_id=document.id) == []
        assert result.reply.content == "Ya existe."

    def test_a_plain_answer_creates_no_draft(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        result = _post(organization, document, editor, "@IA hola", _Model(reply="Hola"))

        assert result.proposal is None


@pytest.mark.django_db
class TestIsolationAndOrdering:
    def test_another_organizations_document_is_not_reachable(self):
        organization, owner, editor, *_ = make_org_with_roles()
        other, other_owner, *_ = make_org_with_roles()
        foreign = _document(other, other_owner)

        with pytest.raises(Http404):
            _post(organization, foreign, editor, "hola")
        with pytest.raises(Http404):
            chat.list_messages(organization=organization, doc_id=foreign.id)

    def test_each_organization_only_lists_its_own_chat(self):
        org_a, owner_a, *_ = make_org_with_roles()
        org_b, owner_b, *_ = make_org_with_roles()
        doc_a, doc_b = _document(org_a, owner_a), _document(org_b, owner_b)
        _post(org_a, doc_a, owner_a, "secreto de A")
        _post(org_b, doc_b, owner_b, "secreto de B")

        assert [m.content for m in chat.list_messages(organization=org_a, doc_id=doc_a.id)] == ["secreto de A"]
        assert [m.content for m in chat.list_messages(organization=org_b, doc_id=doc_b.id)] == ["secreto de B"]

    def test_messages_keep_the_order_they_were_written_in(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        for index in range(6):
            _post(organization, document, owner if index % 2 else editor, f"m{index}")

        listed = chat.list_messages(organization=organization, doc_id=document.id)

        assert [m.content for m in listed] == [f"m{index}" for index in range(6)]
        assert [m.id for m in listed] == sorted(m.id for m in listed)

    def test_the_listing_returns_the_latest_messages_oldest_first(self):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        for index in range(5):
            _post(organization, document, owner, f"m{index}")

        listed = chat.list_messages(organization=organization, doc_id=document.id, limit=3)

        assert [m.content for m in listed] == ["m2", "m3", "m4"]

    def test_the_new_message_is_broadcast_to_the_document_group(self):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)

        with mock.patch("apps.ai_assistant.chat.services.broadcast_event") as broadcast:
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr("django.db.transaction.on_commit", lambda fn: fn())
                _post(organization, document, editor, "@IA hola", _Model(reply="Hola"))

        payloads = [call.kwargs["payload"] for call in broadcast.call_args_list]
        assert [p["type"] for p in payloads] == ["chat.message", "chat.message"]
        assert [p["message"]["content"] for p in payloads] == ["@IA hola", "Hola"]
        assert all(call.kwargs["document_id"] == document.id for call in broadcast.call_args_list)


@pytest.mark.django_db(transaction=True)
def test_several_people_writing_at_once_neither_mix_nor_lose_messages():
    organization, owner, editor, *_ = make_org_with_roles()
    document = _document(organization, owner)
    per_writer = 8

    def write(author, label):
        try:
            for index in range(per_writer):
                _post(organization, document, author, f"{label}-{index}")
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        for future in [pool.submit(write, owner, "owner"), pool.submit(write, editor, "editor")]:
            future.result()

    stored = chat.list_messages(organization=organization, doc_id=document.id, limit=1000)
    assert len(stored) == per_writer * 2
    assert len({m.id for m in stored}) == per_writer * 2
    for author, label in ((owner, "owner"), (editor, "editor")):
        own = [m.content for m in stored if m.author_id == author.id]
        assert own == [f"{label}-{index}" for index in range(per_writer)]
