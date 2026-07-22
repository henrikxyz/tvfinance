"""Structured exceptions raised by tvfinance."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType


class TvFinanceError(Exception):
    """Base class for errors raised by the package.

    Context must contain only non-sensitive diagnostic values. Credentials,
    cookies, authorization headers, and response bodies must never be attached.
    """

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context: Mapping[str, object] = MappingProxyType(dict(context or {}))

    def __str__(self) -> str:
        if not self.context:
            return self.message
        details = ", ".join(
            f"{key}={value!r}" for key, value in sorted(self.context.items())
        )
        return f"{self.message} ({details})"


class ConfigurationError(TvFinanceError):
    """Raised when client configuration is invalid or incomplete."""


class ValidationError(TvFinanceError, ValueError):
    """Raised when a public input fails validation."""


class TransportError(TvFinanceError):
    """Raised when an HTTP or WebSocket operation fails."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        status_code: int | None = None,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message, context=context)
        self.retryable = retryable
        self.status_code = status_code


class RequestTimeoutError(TransportError, TimeoutError):
    """Raised when an operation exceeds its configured deadline."""

    def __init__(
        self,
        message: str = "Request timed out",
        *,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message, retryable=True, context=context)


class RateLimitError(TransportError):
    """Raised when a provider rejects a request due to rate limiting."""

    def __init__(
        self,
        message: str = "Request was rate limited",
        *,
        retry_after: float | None = None,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(
            message,
            retryable=True,
            status_code=429,
            context=context,
        )
        self.retry_after = retry_after


class ProtocolError(TvFinanceError):
    """Raised when a provider response violates the expected protocol."""


class ParseError(ProtocolError):
    """Raised when a response cannot be converted into domain data."""


class OptionalDependencyError(ConfigurationError, ImportError):
    """Raised when an optional interface is used without its extra."""

    def __init__(self, extra: str) -> None:
        super().__init__(
            f"Optional dependencies are missing; install tvfinance[{extra}]",
            context={"extra": extra},
        )
        self.extra = extra
