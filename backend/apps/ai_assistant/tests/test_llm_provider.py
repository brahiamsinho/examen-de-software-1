"""Tests for `apps/ai_assistant/llm_provider.py`'s dispatch logic."""
import pytest
from django.test import override_settings

from apps.ai_assistant.errors import MissingApiKeyError
from apps.ai_assistant.gemini_client import GeminiClient
from apps.ai_assistant.llm_provider import get_active_llm_client
from apps.ai_assistant.openai_client import OpenAiClient


class TestGetActiveLlmClient:
    @override_settings(LLM_PROVIDER="gemini", GEMINI_API_KEY="a-key")
    def test_defaults_to_gemini(self):
        assert isinstance(get_active_llm_client(), GeminiClient)

    @override_settings(LLM_PROVIDER="openai", OPENAI_API_KEY="a-key")
    def test_selects_openai_when_configured(self):
        assert isinstance(get_active_llm_client(), OpenAiClient)

    @override_settings(LLM_PROVIDER="OpenAI", OPENAI_API_KEY="a-key")
    def test_provider_name_is_case_insensitive(self):
        assert isinstance(get_active_llm_client(), OpenAiClient)

    @override_settings(LLM_PROVIDER="mistral")
    def test_an_unknown_provider_raises_a_whole_request_error_not_a_per_command_one(self):
        # MissingApiKeyError (not TranslationError): this runs before any
        # function call exists to translate, so it must be caught by
        # `api.py`'s whole-request exception handlers, not the per-command
        # loop in `service.py`.
        with pytest.raises(MissingApiKeyError):
            get_active_llm_client()

    @override_settings(LLM_PROVIDER="", GEMINI_API_KEY="a-key")
    def test_an_empty_provider_setting_defaults_to_gemini(self):
        assert isinstance(get_active_llm_client(), GeminiClient)
