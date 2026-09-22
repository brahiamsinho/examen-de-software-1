"""Picks which LLM backs the voice assistant, via `settings.LLM_PROVIDER`
(design.md DD180). `service.py` depends only on this function and on
`GeminiClientProtocol` — it never imports `gemini_client`/`openai_client`
directly, so adding a third provider later touches this file and its own
new `<provider>_client.py`, nothing else.
"""
from django.conf import settings

from apps.ai_assistant.errors import MissingApiKeyError
from apps.ai_assistant.gemini_client import GeminiClientProtocol, get_gemini_client
from apps.ai_assistant.openai_client import get_openai_client

_PROVIDERS = {
    "gemini": get_gemini_client,
    "openai": get_openai_client,
}


def get_active_llm_client() -> GeminiClientProtocol:
    """Raises `MissingApiKeyError` (not `TranslationError`) for a bad
    provider name: this runs before any function call exists to translate,
    so it must be one of the two WHOLE-REQUEST failures `api.py` already
    handles cleanly (503), never something only the per-command loop
    catches.
    """
    provider = (settings.LLM_PROVIDER or "gemini").strip().lower()
    factory = _PROVIDERS.get(provider)
    if factory is None:
        raise MissingApiKeyError(
            f"Unknown LLM_PROVIDER '{provider}'; expected one of {sorted(_PROVIDERS)}."
        )
    return factory()
