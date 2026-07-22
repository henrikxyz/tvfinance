"""Core types shared by all tvfinance interfaces."""

from tvfinance.core.cache import MemoryResponseCache, request_cache_key
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
    OptionSeries,
    Quote,
    ResearchData,
    ScreenerRow,
    Symbol,
    SymbolSearchResult,
)
from tvfinance.core.session import AsyncClientSession
from tvfinance.core.settings import ClientSettings, Locale, RetryPolicy
from tvfinance.core.transport import CachedTransport, CurlHttpTransport, RetryTransport
from tvfinance.core.websocket import decode_frames, encode_frame, encode_method

__all__ = [
    "AsyncClientSession",
    "AsyncHttpTransport",
    "AsyncWebSocket",
    "CachedTransport",
    "CalendarEvent",
    "Candle",
    "ClientSettings",
    "ConfigurationError",
    "CurlHttpTransport",
    "HttpRequest",
    "HttpResponse",
    "Locale",
    "MemoryResponseCache",
    "NewsArticle",
    "OptionChainRow",
    "OptionContract",
    "OptionSeries",
    "OptionalDependencyError",
    "ParseError",
    "ProtocolError",
    "Quote",
    "RateLimitError",
    "RequestTimeoutError",
    "ResearchData",
    "RetryPolicy",
    "RetryTransport",
    "ScreenerRow",
    "Symbol",
    "SymbolSearchResult",
    "TransportError",
    "TvFinanceError",
    "ValidationError",
    "decode_frames",
    "encode_frame",
    "encode_method",
    "request_cache_key",
]
