"""Custom exceptions. Callers catch these, not provider-native exceptions,
so swapping a provider never changes what a caller needs to handle."""


class FNewsAIError(Exception):
    """Base class for all errors raised by this package."""


class ProviderError(FNewsAIError):
    """An LLM or search provider call failed (network, auth, rate limit, bad response)."""


class IngestionError(FNewsAIError):
    """Fetching or parsing a source article failed."""


class VerificationTimeoutError(FNewsAIError):
    """The agentic verification loop hit max_search_turns without a final answer."""
