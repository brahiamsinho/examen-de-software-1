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

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str | None = None,
        provider_label: str = "OpenAI",
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        embedding_model: str = "text-embedding-3-small",
    ):
        self._api_key = api_key
        self._model = model
        self._embedding_model = embedding_model
        # `None` keeps the hosted defaults (45s timeout, the SDK's retries).
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        # Set only for an OpenAI-compatible local server (Ollama, vLLM,
        # llama.cpp...): the hosted path never sends a `base_url`.
        self._base_url = base_url
        self._provider_label = provider_label

    @property
    def embedding_model(self) -> str:
        """Names the vectors this client makes: vectors of different models are
        never compared with each other."""
        return self._embedding_model

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in order, from the provider's embeddings API (a
        transformer encoder: texts that mean the same land close together)."""
        if not texts:
            return []
        client = self._sdk_client()
        try:
            response = client.embeddings.create(model=self._embedding_model, input=list(texts))
        except Exception as exc:  # the SDK raises several exception types; all map to one domain error
            raise GeminiRequestError(f"{self._provider_label} embeddings request failed: {exc}") from exc
        return [list(item.embedding) for item in response.data]

    def _sdk_client(self):
        # Imported lazily, same reasoning as the methods below.
        from openai import OpenAI

        # `timeout` is seconds here (httpx convention), unlike Gemini's
        # `HttpOptions.timeout` (milliseconds).
        kwargs: dict[str, object] = {
            "api_key": self._api_key,
            "timeout": self._timeout_seconds or REQUEST_TIMEOUT_MS / 1000,
        }
        if self._max_retries is not None:
            kwargs["max_retries"] = self._max_retries
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return OpenAI(**kwargs)

    def generate_function_calls(
        self,
        *,
        system_instruction: str,
        transcript: str,
        tools: Sequence[Mapping[str, object]],
    ) -> list[GeminiFunctionCall]:
        # The SDK is imported lazily (see `_sdk_client`), same reasoning as
        # `gemini_client.py`: every test injects a fake
        # `GeminiClientProtocol`, so the SDK only needs to be present in
        # production.
        client = self._sdk_client()
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
            raise GeminiRequestError(f"{self._provider_label} request failed: {exc}") from exc

        calls = _extract_function_calls(response)
        if not calls and any(tool.get("name") == "reply_in_chat" for tool in tools):
            # A model often answers a plain question with text instead of calling the
            # reply tool; dropping it would leave the chat silent.
            text = _plain_text(response)
            if text:
                calls = [GeminiFunctionCall(name="reply_in_chat", args={"message": text})]
        return calls

    def generate_function_calls_from_image(
        self,
        *,
        system_instruction: str,
        image_bytes: bytes,
        image_mime_type: str,
        tools: Sequence[Mapping[str, object]],
    ) -> list[GeminiFunctionCall]:
        """Real vision support (confirmed against the currently installed
        `openai` SDK: `gpt-4o-mini`, this project's default
        `settings.OPENAI_MODEL`, accepts multimodal Chat Completions
        content). The image is base64-embedded as a `data:` URI rather than
        uploaded separately — no file-upload/Assistants API round trip
        needed for a single inline image.
        """
        import base64

        client = self._sdk_client()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Replicate the UML class diagram shown in this image.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{image_mime_type};base64,{image_b64}"},
                            },
                        ],
                    },
                ],
                tools=_as_openai_tools(tools),
                tool_choice={"type": "function", "function": {"name": "extract_uml_diagram"}},
            )
        except Exception as exc:  # same one-domain-error mapping as the text path
            raise GeminiRequestError(f"{self._provider_label} request failed: {exc}") from exc

        return _extract_function_calls(response)


def _plain_text(response: object) -> str:
    choices = getattr(response, "choices", None) or []
    content = getattr(getattr(choices[0], "message", None), "content", None) if choices else None
    return content.strip() if isinstance(content, str) else ""


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
    return OpenAiClient(api_key, settings.OPENAI_MODEL, embedding_model=settings.OPENAI_EMBEDDING_MODEL)


def get_local_llm_client() -> OpenAiClient:
    """Factory for an OpenAI-compatible local server (issue #18). Reuses
    `OpenAiClient` because Ollama, vLLM and llama.cpp all speak the same
    Chat Completions protocol; everything comes from the environment, so
    nothing here is tied to one host. Raises `MissingApiKeyError` (the
    whole-request 503 `api.py` already handles) when the URL or the model
    is missing, instead of failing later inside the SDK.
    """
    base_url = (settings.LOCAL_LLM_BASE_URL or "").strip()
    if not base_url:
        raise MissingApiKeyError("LOCAL_LLM_BASE_URL is not configured.")
    model = (settings.LOCAL_LLM_MODEL or "").strip()
    if not model:
        raise MissingApiKeyError("LOCAL_LLM_MODEL is not configured.")
    # The SDK refuses an empty key, but most local servers ignore it.
    api_key = settings.LOCAL_LLM_API_KEY or "not-needed"
    # No retries: a retry on a slow CPU model re-runs the whole generation and
    # multiplies the wait. The timeout is configurable because a model on a
    # CPU-only instance needs far longer than a hosted API.
    return OpenAiClient(
        api_key,
        model,
        base_url=base_url,
        provider_label="Local LLM",
        timeout_seconds=settings.LOCAL_LLM_TIMEOUT_SECONDS,
        max_retries=0,
        embedding_model=settings.LOCAL_EMBEDDING_MODEL,
    )
