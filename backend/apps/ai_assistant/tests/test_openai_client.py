"""Tests for `apps/ai_assistant/openai_client.py`. Same shape as
`test_gemini_client.py`: `get_openai_client()`'s key-presence branching is
tested directly; `OpenAiClient.generate_function_calls`'s response-parsing
logic is tested by monkeypatching `sys.modules["openai"]` with a fake SDK
module — never a real network call.
"""
import json
import sys
import types as python_types
from unittest import mock

import pytest
from django.test import override_settings

from apps.ai_assistant.errors import GeminiRequestError, MissingApiKeyError
from apps.ai_assistant.gemini_client import REQUEST_TIMEOUT_MS
from apps.ai_assistant.openai_client import OpenAiClient, get_openai_client


class TestGetOpenaiClient:
    @override_settings(OPENAI_API_KEY="")
    def test_raises_when_the_api_key_is_unset(self):
        with pytest.raises(MissingApiKeyError):
            get_openai_client()

    @override_settings(OPENAI_API_KEY="a-real-key", OPENAI_MODEL="gpt-test-model")
    def test_returns_a_configured_client_when_the_key_is_set(self):
        client = get_openai_client()

        assert isinstance(client, OpenAiClient)
        assert client._api_key == "a-real-key"
        assert client._model == "gpt-test-model"


def _fake_tool_call(name: str, arguments: str):
    function = mock.Mock()
    function.name = name
    function.arguments = arguments
    tool_call = mock.Mock()
    tool_call.function = function
    return tool_call


def _fake_response(tool_calls):
    message = mock.Mock()
    message.tool_calls = tool_calls
    choice = mock.Mock()
    choice.message = message
    response = mock.Mock()
    response.choices = [choice]
    return response


def _install_fake_openai_module(monkeypatch, *, create):
    """Installs a minimal fake `openai` package into `sys.modules` so
    `from openai import OpenAI` inside `OpenAiClient.generate_function_calls`
    resolves to a test double instead of the real SDK.
    """
    fake_client_instance = mock.Mock()
    fake_client_instance.chat.completions.create = create
    fake_client_class = mock.Mock(return_value=fake_client_instance)

    openai_module = python_types.ModuleType("openai")
    openai_module.OpenAI = fake_client_class

    monkeypatch.setitem(sys.modules, "openai", openai_module)
    return fake_client_class


class TestGenerateFunctionCalls:
    def test_extracts_every_tool_call_from_the_response(self, monkeypatch):
        response = _fake_response(
            [
                _fake_tool_call("add_class", json.dumps({"name": "Persona"})),
                _fake_tool_call(
                    "add_attribute",
                    json.dumps({"class_name": "Persona", "attribute_name": "edad"}),
                ),
            ]
        )
        _install_fake_openai_module(monkeypatch, create=mock.Mock(return_value=response))
        client = OpenAiClient("a-key", "a-model")

        calls = client.generate_function_calls(
            system_instruction="system", transcript="creá una clase Persona", tools=[]
        )

        assert [c.name for c in calls] == ["add_class", "add_attribute"]
        assert calls[0].args == {"name": "Persona"}
        assert calls[1].args == {"class_name": "Persona", "attribute_name": "edad"}

    def test_no_tool_calls_returns_an_empty_list(self, monkeypatch):
        response = _fake_response(None)
        _install_fake_openai_module(monkeypatch, create=mock.Mock(return_value=response))
        client = OpenAiClient("a-key", "a-model")

        calls = client.generate_function_calls(
            system_instruction="system", transcript="hola", tools=[]
        )

        assert calls == []

    def test_malformed_arguments_json_degrades_to_empty_args_instead_of_crashing(self, monkeypatch):
        response = _fake_response([_fake_tool_call("add_class", "not valid json")])
        _install_fake_openai_module(monkeypatch, create=mock.Mock(return_value=response))
        client = OpenAiClient("a-key", "a-model")

        calls = client.generate_function_calls(
            system_instruction="system", transcript="hola", tools=[]
        )

        assert calls == [mock.ANY]
        assert calls[0].name == "add_class"
        assert calls[0].args == {}

    def test_a_sdk_failure_is_wrapped_as_a_gemini_request_error(self, monkeypatch):
        _install_fake_openai_module(
            monkeypatch, create=mock.Mock(side_effect=RuntimeError("boom"))
        )
        client = OpenAiClient("a-key", "a-model")

        with pytest.raises(GeminiRequestError):
            client.generate_function_calls(system_instruction="system", transcript="hola", tools=[])

    def test_constructs_the_sdk_client_with_a_request_timeout(self, monkeypatch):
        # Regression guard, same class of bug already found once with
        # Gemini: no timeout means a slow/stuck upstream hangs forever.
        response = _fake_response(None)
        fake_client_class = _install_fake_openai_module(
            monkeypatch, create=mock.Mock(return_value=response)
        )
        client = OpenAiClient("a-key", "a-model")

        client.generate_function_calls(system_instruction="system", transcript="hola", tools=[])

        _, kwargs = fake_client_class.call_args
        assert kwargs["timeout"] == REQUEST_TIMEOUT_MS / 1000

    def test_wraps_each_tool_in_the_openai_function_envelope(self, monkeypatch):
        response = _fake_response(None)
        fake_client_class = _install_fake_openai_module(
            monkeypatch, create=mock.Mock(return_value=response)
        )
        client = OpenAiClient("a-key", "a-model")
        one_tool = {"name": "add_class", "description": "...", "parameters": {"type": "object"}}

        client.generate_function_calls(
            system_instruction="system", transcript="hola", tools=[one_tool]
        )

        create_call = fake_client_class.return_value.chat.completions.create
        _, kwargs = create_call.call_args
        assert kwargs["tools"] == [{"type": "function", "function": one_tool}]
