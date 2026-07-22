from __future__ import annotations

import pytest

from tvfinance.core import (
    ConfigurationError,
    OptionalDependencyError,
    ParseError,
    ProtocolError,
    RateLimitError,
    RequestTimeoutError,
    TransportError,
    TvFinanceError,
    ValidationError,
)


def test_base_error_without_context() -> None:
    error = TvFinanceError("failed")

    assert str(error) == "failed"
    assert error.context == {}


def test_error_context_is_copied_sorted_and_read_only() -> None:
    source = {"symbol": "NASDAQ:AAPL", "attempt": 2}
    error = TvFinanceError("failed", context=source)
    source["attempt"] = 3

    assert str(error) == "failed (attempt=2, symbol='NASDAQ:AAPL')"
    assert error.context["attempt"] == 2
    with pytest.raises(TypeError):
        error.context["attempt"] = 4  # type: ignore[index]


@pytest.mark.parametrize(
    ("error", "base"),
    [
        (ConfigurationError("config"), TvFinanceError),
        (ValidationError("input"), ValueError),
        (ProtocolError("protocol"), TvFinanceError),
        (ParseError("parse"), ProtocolError),
    ],
)
def test_error_hierarchy(error: Exception, base: type[BaseException]) -> None:
    assert isinstance(error, base)


def test_transport_error_carries_retry_metadata() -> None:
    error = TransportError("offline", retryable=False, status_code=503)

    assert error.retryable is False
    assert error.status_code == 503


def test_timeout_is_retryable_and_compatible_with_builtin() -> None:
    error = RequestTimeoutError(context={"operation": "quote"})

    assert isinstance(error, TimeoutError)
    assert error.retryable is True
    assert error.status_code is None


def test_rate_limit_error_carries_retry_delay() -> None:
    error = RateLimitError(retry_after=1.5)

    assert error.retryable is True
    assert error.status_code == 429
    assert error.retry_after == 1.5


def test_optional_dependency_error_explains_installation() -> None:
    error = OptionalDependencyError("mcp")

    assert isinstance(error, ImportError)
    assert error.extra == "mcp"
    assert "tvfinance[mcp]" in str(error)
