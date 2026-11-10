"""Semantic memory of the chat: when asked, the AI is also shown the earlier team
conversation that means the same thing as the question, from other diagrams of the
same organization or from further back in this one. Never from another organization."""
import re

import pytest
from django.utils import timezone

from apps.ai_assistant import chat, memory
from apps.ai_assistant.errors import GeminiRequestError
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.ai_assistant.models import ChatMessage
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services

_DIMENSIONS = 400


def _words(text):
    return {word for word in re.findall(r"[a-záéíóúñ]+", text.lower()) if len(word) > 3}


def _vector(text):
    # A toy "meaning": one dimension per word. Texts sharing words are close.
    vector = [0.0] * _DIMENSIONS
    for word in _words(text):
        vector[sum(ord(letter) * (index + 1) for index, letter in enumerate(word)) % _DIMENSIONS] = 1.0
    return vector


class _Model:
    """Records what the model was sent and can embed text."""

    embedding_model = "toy-embedder"

    def __init__(self, reply="Claro.", embed_error=None):
        self.requests = []
        self.embedded = []
        self._reply = reply
        self._embed_error = embed_error

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        self.requests.append(transcript)
        return [GeminiFunctionCall(name="reply_in_chat", args={"message": self._reply})]

    def embed(self, texts):
        if self._embed_error:
            raise self._embed_error
        self.embedded.extend(texts)
        return [_vector(text) for text in texts]


class _ModelWithoutEmbeddings:
    def __init__(self):
        self.requests = []

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        self.requests.append(transcript)
        return [GeminiFunctionCall(name="reply_in_chat", args={"message": "Claro."})]


@pytest.fixture(autouse=True)
def synchronous(monkeypatch):
    monkeypatch.setattr(memory, "_run_in_background", lambda job: job())


def _document(organization, owner, name):
    return services.create_document(organization=organization, owner_id=str(owner.id), name=name, now=timezone.now())


def _say(organization, document, author, text, model):
    return chat.post_message(organization=organization, doc_id=document.id, author=author, content=text, gemini=model)


def _ask(organization, document, author, text, model):
    return _say(organization, document, author, text, model)


@pytest.mark.django_db
class TestRecall:
    def test_the_ai_is_shown_a_related_conversation_from_another_diagram_with_where_it_came_from(self):
        organization, owner, editor, *_ = make_org_with_roles()
        sales = _document(organization, owner, "Ventas")
        library = _document(organization, owner, "Biblioteca")
        model = _Model()
        _say(organization, sales, editor, "Persona lleva carnet de identidad unico", model)
        _say(organization, sales, owner, "Reunion el viernes para revisar facturas", model)

        _ask(organization, library, owner, "@IA que atributos lleva Persona, el carnet?", model)

        sent = model.requests[-1]
        assert "earlier team conversation" in sent.lower()
        assert "Persona lleva carnet de identidad unico" in sent
        assert "Ventas" in sent
        assert (editor.full_name or editor.email) in sent
        assert "Reunion el viernes" not in sent  # unrelated: left out

    def test_it_reaches_back_in_the_same_diagram_beyond_the_window_the_model_already_sees(self, monkeypatch):
        organization, owner, editor, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")
        model = _Model()
        monkeypatch.setattr(chat, "CONTEXT_MESSAGES", 3)
        _say(organization, board, editor, "Persona lleva carnet de identidad unico", model)
        for filler in ("uno uno", "dos dos", "tres tres"):
            _say(organization, board, owner, filler, model)

        _ask(organization, board, owner, "@IA que atributos lleva Persona, el carnet?", model)

        assert "Persona lleva carnet de identidad unico" in model.requests[-1]

    def test_what_the_model_already_sees_in_the_chat_is_not_repeated_as_a_memory(self):
        organization, owner, editor, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")
        model = _Model()
        _say(organization, board, editor, "Persona lleva carnet de identidad unico", model)

        _ask(organization, board, owner, "@IA que atributos lleva Persona, el carnet?", model)

        assert model.requests[-1].count("Persona lleva carnet de identidad unico") == 1

    def test_nothing_from_another_organization_is_ever_shown(self):
        organization, owner, editor, *_ = make_org_with_roles()
        other_organization, other_owner, *_ = make_org_with_roles()
        secret = _document(other_organization, other_owner, "Secreto")
        board = _document(organization, owner, "Tablero")
        model = _Model()
        _say(other_organization, secret, other_owner, "Persona lleva carnet de identidad unico", model)

        _ask(organization, board, owner, "@IA que atributos lleva Persona, el carnet?", model)

        assert "carnet de identidad" not in model.requests[-1]
        assert "Secreto" not in model.requests[-1]

    def test_with_no_related_conversation_the_prompt_has_no_memory_section(self):
        organization, owner, editor, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")
        model = _Model()

        _ask(organization, board, owner, "@IA hola", model)

        assert "earlier team conversation" not in model.requests[-1].lower()

    def test_vectors_from_a_different_embedding_model_are_ignored(self):
        organization, owner, editor, *_ = make_org_with_roles()
        sales = _document(organization, owner, "Ventas")
        library = _document(organization, owner, "Biblioteca")
        model = _Model()
        _say(organization, sales, editor, "Persona lleva carnet de identidad unico", model)
        ChatMessage.all_objects.filter(document_id=sales.id).update(embedding_model="another-model")

        _ask(organization, library, owner, "@IA que atributos lleva Persona, el carnet?", model)

        assert "carnet de identidad" not in model.requests[-1]


@pytest.mark.django_db
class TestRemembering:
    def test_a_posted_message_is_stored_with_its_vector_and_the_model_that_made_it(self):
        organization, owner, editor, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")

        result = _say(organization, board, editor, "Persona lleva carnet de identidad unico", _Model())

        stored = ChatMessage.all_objects.get(id=result.message.id)
        assert stored.embedding_model == "toy-embedder"
        assert len(stored.embedding) == _DIMENSIONS

    def test_the_ai_reply_is_remembered_too(self):
        organization, owner, editor, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")

        result = _ask(organization, board, owner, "@IA que atributos lleva Persona?", _Model(reply="Persona lleva nombre"))

        assert ChatMessage.all_objects.get(id=result.reply.id).embedding_model == "toy-embedder"


@pytest.mark.django_db
class TestBackfill:
    def _old_messages(self, organization, owner, board, count):
        # Written before the memory existed: no vector yet.
        return [
            ChatMessage.all_objects.create(organization=organization, document_id=board.id, author=owner, content=f"mensaje numero {n}")
            for n in range(count)
        ]

    def test_it_gives_a_vector_to_the_messages_that_have_none_and_reports_how_many(self):
        organization, owner, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")
        old = self._old_messages(organization, owner, board, 3)

        done = memory.backfill(_Model(), batch_size=2)

        assert done == 3
        assert all(ChatMessage.all_objects.get(id=item.id).embedding_model == "toy-embedder" for item in old)

    def test_messages_that_already_have_a_vector_are_not_embedded_again(self):
        organization, owner, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")
        self._old_messages(organization, owner, board, 2)
        model = _Model()
        memory.backfill(model)
        model.embedded.clear()

        assert memory.backfill(model) == 0
        assert model.embedded == []

    def test_a_provider_without_embeddings_is_reported_instead_of_silently_doing_nothing(self):
        with pytest.raises(memory.EmbeddingsUnavailable):
            memory.backfill(_ModelWithoutEmbeddings())


@pytest.mark.django_db
class TestMemoryNeverBreaksTheChat:
    def test_a_failing_embeddings_provider_still_lets_the_ai_answer(self):
        organization, owner, editor, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")
        model = _Model(reply="Aqui estoy", embed_error=GeminiRequestError("embeddings are down"))

        result = _ask(organization, board, owner, "@IA hola", model)

        assert result.reply.content == "Aqui estoy"
        assert result.ai_error is None

    def test_a_provider_without_embeddings_works_without_memory(self):
        organization, owner, editor, *_ = make_org_with_roles()
        board = _document(organization, owner, "Tablero")
        model = _ModelWithoutEmbeddings()

        result = _ask(organization, board, owner, "@IA hola", model)

        assert result.reply.content == "Claro."
        assert ChatMessage.all_objects.get(id=result.message.id).embedding_model == ""
