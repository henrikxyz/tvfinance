"""Core types shared by all tvfinance interfaces."""

from tvfinance.core.contracts import (
    AsyncHttpTransport,
    AsyncWebSocket,
    HttpRequest,
    HttpResponse,
)
from tvfinance.core.exceptions import (
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
from tvfinance.core.models import (
    CalendarEvent,
    Candle,
    NewsArticle,
    OptionChainRow,
    OptionContract,
    Quote,
    Symbol,
    SymbolSearchResult,
)
from tvfinance.core.settings import ClientSettings, Locale, RetryPolicy

__all__ = [
    "AsyncHttpTransport",
    "AsyncWebSocket",
    "CalendarEvent",
    "Candle",
    "ClientSettings",
    "ConfigurationError",
    "HttpRequest",
    "HttpResponse",
    "Locale",
    "NewsArticle",
    "OptionChainRow",
    "OptionContract",
    "OptionalDependencyError",
    "ParseError",
    "ProtocolError",
    "Quote",
    "RateLimitError",
    "RequestTimeoutError",
    "RetryPolicy",
    "Symbol",
    "SymbolSearchResult",
    "TransportError",
    "TvFinanceError",
    "ValidationError",
]
