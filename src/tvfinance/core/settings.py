"""Validated client configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from tvfinance.core.validation import normalize_locale, positive_number

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


@dataclass(frozen=True, slots=True)
class Locale:
    """Language and region used for provider requests."""

    language: str = "en"
    region: str = "US"

    def __post_init__(self) -> None:
        language, region = normalize_locale(self.language, self.region)
        object.__setattr__(self, "language", language)
        object.__setattr__(self, "region", region)

    @property
    def accept_language(self) -> str:
        return f"{self.language}-{self.region},{self.language};q=0.9"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry and backoff limits for transport operations."""

    attempts: int = 3
    base_delay: float = 0.5
    maximum_delay: float = 8.0
    retry_statuses: frozenset[int] = field(
        default_factory=lambda: frozenset({429, 500, 502, 503, 504})
    )

    def __post_init__(self) -> None:
        if self.attempts < 1:
            positive_number(float(self.attempts), field="attempts")
        positive_number(self.base_delay, field="base_delay")
        positive_number(self.maximum_delay, field="maximum_delay")


@dataclass(frozen=True, slots=True)
class ClientSettings:
    """Configuration shared by sync and async clients."""

    timeout: float = 30.0
    locale: Locale = field(default_factory=Locale)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    user_agent: str = DEFAULT_USER_AGENT

    def __post_init__(self) -> None:
        positive_number(self.timeout, field="timeout")
