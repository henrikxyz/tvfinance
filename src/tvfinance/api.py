"""Stable synchronous functional API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tvfinance.client import Client
from tvfinance.core.models import (
    CalendarEvent,
    NewsArticle,
    OptionChainRow,
    Quote,
    ScreenerRow,
    Symbol,
    SymbolSearchResult,
)


def search(query: str) -> list[SymbolSearchResult]:
    return Client().search(query)


def quote(symbol: str | Symbol) -> Quote:
    return Client().quote(symbol)


def quotes(symbols: list[str | Symbol]) -> dict[str, Quote | None]:
    return Client().quotes(symbols)


def screener(**kwargs: Any) -> list[ScreenerRow]:
    return Client().screener(**kwargs)


def options_chain(
    symbol: str | Symbol, *, expiration: int, root: str
) -> list[OptionChainRow]:
    return Client().options_chain(symbol, expiration=expiration, root=root)


def news(symbol: str | Symbol, **kwargs: Any) -> list[NewsArticle]:
    return Client().news(symbol, **kwargs)


def economic_calendar(
    *,
    from_date: datetime,
    to_date: datetime,
    countries: list[str] | None = None,
) -> list[CalendarEvent]:
    return Client().economic_calendar(
        from_date=from_date, to_date=to_date, countries=countries
    )
