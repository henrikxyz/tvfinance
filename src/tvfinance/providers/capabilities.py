"""Machine-readable provider capability inventory."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProviderCapability:
    """One supported data capability and its compatibility strategy."""

    name: str
    transport: str
    stability: str
    contract_fixture: bool
    live_check: bool


CAPABILITIES = (
    ProviderCapability("search", "HTTP JSON", "public-unofficial", True, True),
    ProviderCapability("quotes", "HTTP JSON", "public-unofficial", True, True),
    ProviderCapability("quote_stream", "WebSocket", "public-unofficial", True, False),
    ProviderCapability("history", "WebSocket", "public-unofficial", True, False),
    ProviderCapability("screener", "HTTP JSON", "public-unofficial", True, False),
    ProviderCapability(
        "options", "HTTP JSON/WebSocket", "public-unofficial", True, False
    ),
    ProviderCapability("news", "HTTP JSON/HTML", "public-unofficial", True, False),
    ProviderCapability("calendars", "HTTP JSON", "public-unofficial", True, False),
    ProviderCapability("research", "HTTP HTML", "public-unofficial", True, False),
)


def capabilities() -> tuple[ProviderCapability, ...]:
    """Return the immutable provider capability inventory."""
    return CAPABILITIES
