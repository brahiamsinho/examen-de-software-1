"""Tests for `apps/ai_assistant/gemini_client.py`.

`get_gemini_client()`'s key-presence branching is tested directly (no SDK
involved at all — this is the real, exercised-in-production path while
`GEMINI_API_KEY` stays empty). `GeminiClient.generate_function_calls`'s own
response-parsing logic is tested by monkeypatching `sys.modules["google"]`
with a fake SDK module — never a real network call, and never requires the
real `google-genai` package to be importable in the test process.
"""
import sys
import types as python_types
from unittest import mock

import pytest
from django.test import override_settings

from apps.ai_assistant.errors import GeminiRequestError, MissingApiKeyError
from apps.ai_assistant.gemini_client import (
    REQUEST_TIMEOUT_MS,
    GeminiClient,
    get_gemini_client,
)


class TestGetGeminiClient:
    @override_settings(GEMINI_API_KEY="")
    def test_raises_when_the_api_key_is_unset(self):
        with pytest.raises(MissingApiKeyError):
            get_gemini_client()

    @override_settings(GEMINI_API_KEY="a-real-key", GEMINI_MODEL="gemini-test-model")
    def test_returns_a_configured_client_when_the_key_is_set(self):
        client = get_gemini_client()

        assert isinstance(client, GeminiClient)
        assert client._api_key == "a-real-key"
        assert client._model == "gemini-test-model"


def _fake_part(name: str | None, args: dict | None):
    part = mock.Mock()
    if name is None:
        part.function_call = None
    else:
        function_call = mock.Mock()
        function_call.name = name
        function_call.args = args
        part.function_call = function_call
    return part


def _fake_response(parts):
    content = mock.Mock()
    content.parts = parts
    candidate = mock.Mock()
    candidate.content = content
    response = mock.Mock()
    response.candidates = [candidate]
    return response


def _install_fake_genai_module(monkeypatch, *, generate_content):
    """Installs a minimal fake `google.genai` package into `sys.modules` so
    `from google import genai` inside `GeminiClient.generate_function_calls`
    resolves to a test double instead of the real SDK.
    """
    fake_client_instance = mock.Mock()
    fake_client_instance.models.generate_content = generate_content
    fake_client_class = mock.Mock(return_value=fake_client_instance)

    genai_module = python_types.ModuleType("google.genai")
    genai_module.Client = fake_client_class

    types_module = python_types.ModuleType("google.genai.types")
    types_module.GenerateContentConfig = mock.Mock(side_effect=lambda **kwargs: kwargs)
    types_module.Tool = mock.Mock(side_effect=lambda **kwargs: kwargs)
    types_module.HttpOptions = mock.Mock(side_effect=lambda **kwargs: kwargs)

    google_module = python_types.ModuleType("google")
    google_module.genai = genai_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.genai", genai_module)
    monkeypatch.setitem(sys.modules, "google.genai.types", types_module)
    return fake_client_class


class TestGenerateFunctionCalls:
    def test_extracts_every_function_call_from_the_response(self, monkeypatch):
        response = _fake_response(
            [
                _fake_part("add_class", {"name": "Persona"}),
                _fake_part(None, None),  # a plain-text part carries no function_call
                _fake_part("add_attribute", {"class_name": "Persona", "attribute_name": "edad"}),
            ]
        )
        _install_fake_genai_module(monkeypatch, generate_content=mock.Mock(return_value=response))
        client = GeminiClient("a-key", "a-model")

        calls = client.generate_function_calls(
            system_instruction="system", transcript="creá una clase Persona", tools=[]
        )

        assert [c.name for c in calls] == ["add_class", "add_attribute"]
        assert calls[0].args == {"name": "Persona"}
        assert calls[1].args == {"class_name": "Persona", "attribute_name": "edad"}

    def test_constructs_the_sdk_client_with_a_request_timeout(self, monkeypatch):
        # Regression guard: the SDK has no default timeout, so a slow/stuck
        # upstream used to hang this request forever (found in production).
        response = _fake_response([])
        fake_client_class = _install_fake_genai_module(
            monkeypatch, generate_content=mock.Mock(return_value=response)
        )
        client = GeminiClient("a-key", "a-model")

        client.generate_function_calls(system_instruction="system", transcript="hola", tools=[])

        _, kwargs = fake_client_class.call_args
        assert kwargs["http_options"] == {"timeout": REQUEST_TIMEOUT_MS}

    def test_no_candidates_returns_an_empty_list(self, monkeypatch):
        response = mock.Mock()
        response.candidates = []
        _install_fake_genai_module(monkeypatch, generate_content=mock.Mock(return_value=response))
        client = GeminiClient("a-key", "a-model")

        calls = client.generate_function_calls(
            system_instruction="system", transcript="hola", tools=[]
        )

        assert calls == []

    def test_a_sdk_failure_is_wrapped_as_a_gemini_request_error(self, monkeypatch):
        _install_fake_genai_module(
            monkeypatch, generate_content=mock.Mock(side_effect=RuntimeError("boom"))
        )
        client = GeminiClient("a-key", "a-model")

        with pytest.raises(GeminiRequestError):
            client.generate_function_calls(system_instruction="system", transcript="hola", tools=[])


class TestGenerateFunctionCallsFromImage:
    def test_raises_a_clean_not_supported_error_without_touching_the_sdk(self):
        # No fake `google.genai` module installed at all: this must raise
        # before ever importing the SDK, proving image import is genuinely
        # unimplemented for Gemini rather than crashing with an AttributeError.
        client = GeminiClient("a-key", "a-model")

        with pytest.raises(GeminiRequestError, match="LLM_PROVIDER=openai"):
            client.generate_function_calls_from_image(
                system_instruction="system",
                image_bytes=b"fake-bytes",
                image_mime_type="image/png",
                tools=[],
            )
