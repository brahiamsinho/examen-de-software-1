"""Domain errors for the ai_assistant app (voice-driven diagram editing).

Every error here is caught before it can surface as an unhandled 500:
`MissingApiKeyError`/`GeminiRequestError` at the API boundary (`api.py`'s
exception handlers), the `TranslationError` family per-command inside
`service.apply_voice_command` (the partial-failure policy documented
there — a bad reference in command 2 of 3 must not crash commands 1 and 3).
"""


class AiAssistantError(Exception):
    """Base class for every ai_assistant failure."""


class MissingApiKeyError(AiAssistantError):
    """`GEMINI_API_KEY` is not configured (env.example: empty until a real
    key is provisioned)."""


class GeminiRequestError(AiAssistantError):
    """The Gemini API call itself failed: network, auth, quota, or a
    malformed response. Never a partial-command concern — this fails the
    whole voice command before any translation/submission is attempted."""


class InvalidImageError(AiAssistantError):
    """The uploaded diagram image failed a pre-flight check in `api.py`
    (unsupported content type or over the size limit) before any LLM call
    was attempted. Handled by `api.py`'s exception handler -> 400."""


class TranslationError(AiAssistantError):
    """One Gemini function call could not be translated into a `CommandIn`
    payload. Caught per-command in `service.py`, never lets one bad
    reference abort an entire multi-command utterance."""


class UnsupportedFunctionCallError(TranslationError):
    def __init__(self, function_name: str):
        super().__init__(f"Unsupported function call: {function_name!r}")
        self.function_name = function_name


class UnknownClassReferenceError(TranslationError):
    def __init__(self, reference: str):
        super().__init__(
            f"Unknown class or member {reference!r}: it does not exist in this diagram "
            "and is not being created earlier in this same request"
        )
        self.reference = reference


class RelationshipNotFoundError(TranslationError):
    def __init__(self, source_name: str, target_name: str):
        super().__init__(f"No relationship found between {source_name!r} and {target_name!r}")


class AmbiguousRelationshipError(TranslationError):
    def __init__(self, source_name: str, target_name: str, count: int):
        super().__init__(
            f"{count} relationships found between {source_name!r} and {target_name!r}; "
            "state a kind (association, aggregation, composition, generalization) to disambiguate"
        )
