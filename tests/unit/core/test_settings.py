from __future__ import annotations

import pytest

from tvfinance.core import ClientSettings, Locale, RetryPolicy, ValidationError


def test_locale_and_client_defaults() -> None:
    locale = Locale("ZH", "tw")
    settings = ClientSettings(locale=locale)
    assert locale.accept_language == "zh-TW,zh;q=0.9"
    assert settings.timeout == 30.0
    assert settings.retry.attempts == 3


@pytest.mark.parametrize(
    "policy",
    [
        {"attempts": 0},
        {"base_delay": 0},
        {"maximum_delay": 0},
    ],
)
def test_invalid_retry_policy(policy: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        RetryPolicy(**policy)  # type: ignore[arg-type]


def test_invalid_client_timeout() -> None:
    with pytest.raises(ValidationError):
        ClientSettings(timeout=0)
