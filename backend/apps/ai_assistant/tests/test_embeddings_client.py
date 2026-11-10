"""`OpenAiClient.embed`: turns texts into vectors through the provider's embeddings API
(hosted OpenAI, or any OpenAI-compatible local server such as Ollama)."""
import sys
import types as python_types
from unittest import mock

import pytest
from django.test import override_settings

from apps.ai_assistant.errors import GeminiRequestError
from apps.ai_assistant.openai_client import OpenAiClient, get_local_llm_client, get_openai_client


def _install_fake_sdk(monkeypatch, *, create):
    instance = mock.Mock()
    instance.embeddings.create = create
    openai_module = python_types.ModuleType("openai")
    openai_module.OpenAI = mock.Mock(return_value=instance)
    monkeypatch.setitem(sys.modules, "openai", openai_module)


def _response(*vectors):
    return mock.Mock(data=[mock.Mock(embedding=vector, index=position) for position, vector in enumerate(vectors)])


def test_embed_returns_one_vector_per_text_in_order(monkeypatch):
    create = mock.Mock(return_value=_response([1.0, 0.0], [0.0, 1.0]))
    _install_fake_sdk(monkeypatch, create=create)

    vectors = OpenAiClient("key", "chat-model", embedding_model="embed-model").embed(["uno", "dos"])

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert create.call_args.kwargs == {"model": "embed-model", "input": ["uno", "dos"]}


def test_embed_names_the_model_so_vectors_of_different_models_are_never_mixed():
    assert OpenAiClient("key", "chat-model", embedding_model="embed-model").embedding_model == "embed-model"


def test_a_failing_provider_is_reported_as_the_domain_error(monkeypatch):
    _install_fake_sdk(monkeypatch, create=mock.Mock(side_effect=RuntimeError("down")))

    with pytest.raises(GeminiRequestError, match="OpenAI embeddings request failed"):
        OpenAiClient("key", "chat-model").embed(["hola"])


def test_embedding_nothing_does_not_call_the_provider(monkeypatch):
    create = mock.Mock()
    _install_fake_sdk(monkeypatch, create=create)

    assert OpenAiClient("key", "chat-model").embed([]) == []
    create.assert_not_called()


@override_settings(OPENAI_API_KEY="k", OPENAI_EMBEDDING_MODEL="text-embedding-test")
def test_the_hosted_factory_reads_its_embedding_model_from_the_environment():
    assert get_openai_client().embedding_model == "text-embedding-test"


@override_settings(LOCAL_LLM_BASE_URL="http://ollama:11434/v1", LOCAL_LLM_MODEL="m", LOCAL_EMBEDDING_MODEL="nomic-test")
def test_the_local_factory_reads_its_embedding_model_from_the_environment():
    assert get_local_llm_client().embedding_model == "nomic-test"
