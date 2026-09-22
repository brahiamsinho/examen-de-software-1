"""Injectable OpenAI client wrapper — an alternate `GeminiClientProtocol`
implementation (the protocol is structural/provider-agnostic despite its
name; see design.md DD180). Added because Gemini's API showed 19-25s+
round-trip latency, sometimes exceeding even a 45s timeout, from one dev
machine's network, while OpenAI answered in well under a second for the
same kind of request — this gives that environment a working alternative
without discarding the Gemini path (mirrors it structurally, follows
`gemini_client.py`'s exact conventions: lazy SDK import, an injectable
`Protocol`, a `get_*_client()` factory that raises `MissingApiKeyError`
immediately rather than deferring to a confusing SDK-level auth failure).
"""
from collections.abc import Mapping, Sequence

from django.conf import settings

from apps.ai_assistant.errors import GeminiRequestError, MissingApiKeyError
from apps.ai_assistant.gemini_client import REQUEST_TIMEOUT_MS, GeminiFunctionCall


def _as_openai_tools(tools: Sequence[Mapping[str, object]]) -> list[dict]:
    """`tools.TOOLS` is already a plain JSON-Schema-shaped list (see its own
    doc comment) — OpenAI just wraps each entry in a `{"type": "function",
    "function": {...}}` envelope, no field-by-field translation needed.
    """
    return [{"type": "function", "function": dict(tool)} for tool in tools]


class OpenAiClient:
    """Real `openai`-backed implementation, constructed only by
    `get_openai_client()` — nothing else reads `settings.OPENAI_API_KEY`
    directly, matching `gemini_client.get_gemini_client()`'s convention.
    """

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    def generate_function_calls(
        self,
        *,
        system_instruction: str,
        transcript: str,
        tools: Sequence[Mapping[str, object]],
    ) -> list[GeminiFunctionCall]:
        # Imported lazily, same reasoning as `gemini_client.py`: every test
        # injects a fake `GeminiClientProtocol` and never constructs a real
        # `OpenAiClient`, so the SDK only needs to be present in production.
        from openai import OpenAI

        # `timeout` is seconds here (httpx convention), unlike Gemini's
        # `HttpOptions.timeout` (milliseconds) — same underlying no-default-
        # timeout problem this project already hit once, avoided up front.
        client = OpenAI(api_key=self._api_key, timeout=REQUEST_TIMEOUT_MS / 1000)
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": transcript},
                ],
                tools=_as_openai_tools(tools),
            )
        except Exception as exc:  # the SDK raises several exception types; all map to one domain error
            raise GeminiRequestError(f"OpenAI request failed: {exc}") from exc

        return _extract_function_calls(response)


def _extract_function_calls(response: object) -> list[GeminiFunctionCall]:
    import json

    calls: list[GeminiFunctionCall] = []
    choices = getattr(response, "choices", None) or []
    for choice in choices:
        message = getattr(choice, "message", None)
        tool_calls = getattr(message, "tool_calls", None) or []
        for tool_call in tool_calls:
            function = getattr(tool_call, "function", None)
            if function is None:
                continue
            try:
                args = json.loads(function.arguments) if function.arguments else {}
            except (json.JSONDecodeError, TypeError):
                args = {}
            calls.append(GeminiFunctionCall(name=function.name, args=args))
    return calls


def get_openai_client() -> OpenAiClient:
    """Factory read by `llm_provider.py`, mirroring
    `gemini_client.get_gemini_client()`. Raises `MissingApiKeyError`
    immediately rather than deferring to a confusing SDK-level auth
    failure: `OPENAI_API_KEY` is genuinely empty until provisioned
    (`env.example`).
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise MissingApiKeyError("OPENAI_API_KEY is not configured.")
    return OpenAiClient(api_key, settings.OPENAI_MODEL)
