"""Typed tools for financial market data research."""

from __future__ import annotations

from tvfinance.api import (
    economic_calendar,
    news,
    options_chain,
    quote,
    quotes,
    screener,
    search,
)
from tvfinance.client import AsyncClient, Client
from tvfinance.core.exceptions import TvFinanceError
from tvfinance.core.models import (
    CalendarEvent,
    Candle,
    NewsArticle,
    OptionChainRow,
    OptionContract,
    Quote,
    ScreenerRow,
    Symbol,
    SymbolSearchResult,
)
from tvfinance.ticker import Ticker

__version__ = "2.0.0.dev0"

__all__ = [
    "AsyncClient",
    "CalendarEvent",
    "Candle",
    "Client",
    "NewsArticle",
    "OptionChainRow",
    "OptionContract",
    "Quote",
    "ScreenerRow",
    "Symbol",
    "SymbolSearchResult",
    "Ticker",
    "TvFinanceError",
    "__version__",
    "economic_calendar",
    "news",
    "options_chain",
    "quote",
    "quotes",
    "screener",
    "search",
]
