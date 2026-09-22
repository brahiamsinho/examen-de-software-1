"""Injectable Gemini client wrapper (the `google-genai` SDK), mirroring
`apps.backend_deployments.runner_client`'s `RunnerClientProtocol` pattern:
every caller depends on `GeminiClientProtocol`, never the concrete SDK
client, so tests inject a fake and never make a real network call.
"""
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

from apps.ai_assistant.errors import GeminiRequestError, MissingApiKeyError

# Milliseconds (the SDK's own unit for `HttpOptions.timeout`). Real-world
# measurement against the live API (see DECISIONS_LOG DD180) showed 19-25s+
# round trips for a TRIVIAL prompt from one dev machine's network, with high
# variance run to run — this is network/latency, not the model "thinking"
# (disabling thinking_config didn't help). 45s gives real requests (longer
# prompts, function-calling) room without reverting to no-timeout-at-all.
REQUEST_TIMEOUT_MS = 45_000


@dataclass(frozen=True)
class GeminiFunctionCall:
    """One function call Gemini decided to make, already stripped of any
    SDK-specific wrapper type — the shape `translator.py` consumes."""

    name: str
    args: Mapping[str, object]


class GeminiClientProtocol(Protocol):
    def generate_function_calls(
        self,
        *,
        system_instruction: str,
        transcript: str,
        tools: Sequence[Mapping[str, object]],
    ) -> list[GeminiFunctionCall]: ...


class GeminiClient:
    """Real `google-genai`-backed implementation. Constructed only by
    `get_gemini_client()` — nothing else reads `settings.GEMINI_API_KEY`
    directly, matching `runner_client.get_runner_client()`'s convention.
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
        # Imported lazily so importing this module (and everything that
        # transitively imports it, e.g. `service.py`, `api.py`) never
        # requires the SDK to already be importable — every test injects a
        # fake `GeminiClientProtocol` and never constructs a real
        # `GeminiClient`, so the SDK only needs to be present in production.
        from google import genai
        from google.genai import types

        # The SDK has NO default timeout (confirmed: `HttpOptions.timeout`
        # defaults to `None`, milliseconds) — an unresponsive/slow upstream
        # would otherwise hang this request forever, which is exactly what
        # happened in production the first time this was exercised for
        # real. `REQUEST_TIMEOUT_MS` below is the fix; 502 is the caller's
        # correct outcome for a timeout, same as any other request failure.
        client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
        )
        try:
            response = client.models.generate_content(
                model=self._model,
                contents=transcript,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[types.Tool(function_declarations=list(tools))],
                ),
            )
        except Exception as exc:  # the SDK raises several exception types; all map to one domain error
            raise GeminiRequestError(f"Gemini request failed: {exc}") from exc

        return _extract_function_calls(response)


def _extract_function_calls(response: object) -> list[GeminiFunctionCall]:
    calls: list[GeminiFunctionCall] = []
    for candidate in getattr(response, "candidates", None) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            function_call = getattr(part, "function_call", None)
            if function_call is not None:
                calls.append(
                    GeminiFunctionCall(
                        name=function_call.name, args=dict(function_call.args or {})
                    )
                )
    return calls


def get_gemini_client() -> GeminiClientProtocol:
    """Factory read by `service.py`, mirroring `runner_client.get_runner_client()`.

    Raises `MissingApiKeyError` immediately rather than deferring to a
    confusing SDK-level auth failure: `GEMINI_API_KEY` is genuinely empty
    until the user provisions a real key (env.example), so this path is
    exercised for real, not just in tests.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise MissingApiKeyError("GEMINI_API_KEY is not configured.")
    return GeminiClient(api_key, settings.GEMINI_MODEL)
