"""Stable asynchronous functional API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tvfinance.client import AsyncClient
from tvfinance.core.models import (
    CalendarEvent,
    NewsArticle,
    OptionChainRow,
    Quote,
    ScreenerRow,
    Symbol,
    SymbolSearchResult,
)


async def search(query: str) -> list[SymbolSearchResult]:
    async with AsyncClient() as client:
        return await client.search(query)


async def quote(symbol: str | Symbol) -> Quote:
    async with AsyncClient() as client:
        return await client.quote(symbol)


async def quotes(symbols: list[str | Symbol]) -> dict[str, Quote | None]:
    async with AsyncClient() as client:
        return await client.quotes(symbols)


async def screener(**kwargs: Any) -> list[ScreenerRow]:
    async with AsyncClient() as client:
        return await client.screener(**kwargs)


async def options_chain(
    symbol: str | Symbol, *, expiration: int, root: str
) -> list[OptionChainRow]:
    async with AsyncClient() as client:
        return await client.options_chain(symbol, expiration=expiration, root=root)


async def news(symbol: str | Symbol, **kwargs: Any) -> list[NewsArticle]:
    async with AsyncClient() as client:
        return await client.news(symbol, **kwargs)


async def economic_calendar(
    *,
    from_date: datetime,
    to_date: datetime,
    countries: list[str] | None = None,
) -> list[CalendarEvent]:
    async with AsyncClient() as client:
        return await client.economic_calendar(
            from_date=from_date, to_date=to_date, countries=countries
        )


__all__ = [
    "AsyncClient",
    "economic_calendar",
    "news",
    "options_chain",
    "quote",
    "quotes",
    "screener",
    "search",
]
