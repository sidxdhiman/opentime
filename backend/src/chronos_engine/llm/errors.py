"""Typed LLM provider errors.

Providers raise these instead of leaking raw HTTP / transport exceptions, so
that the rest of ChronOS can react to a typed failure without crashing. The
error type is carried on the exception class so callers can branch on it.
"""


class LLMProviderError(Exception):
    """Base class for all typed LLM provider errors."""


class LLMConnectionError(LLMProviderError):
    """The provider endpoint could not be reached (e.g. connection refused)."""


class LLMTimeoutError(LLMProviderError):
    """The provider did not respond within the configured timeout."""


class LLMModelUnavailableError(LLMProviderError):
    """The requested model is not available on the provider."""


class LLMInvalidResponseError(LLMProviderError):
    """The provider returned a malformed or incomplete response."""


class LLMDisabledError(LLMProviderError):
    """The provider is configured but not enabled."""
