"""Stable asynchronous functional API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from tvfinance.client import AsyncClient
from tvfinance.core.models import (
    CalendarEvent,
    Candle,
    NewsArticle,
    OptionChainRow,
    OptionSeries,
    Quote,
    ResearchData,
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


async def stream_quotes(symbols: list[str | Symbol]) -> AsyncIterator[Quote]:
    async with AsyncClient() as client:
        async for item in client.stream_quotes(symbols):
            yield item


async def screener(**kwargs: Any) -> list[ScreenerRow]:
    async with AsyncClient() as client:
        return await client.screener(**kwargs)


async def options_chain(
    symbol: str | Symbol,
    *,
    expiration: int | None = None,
    root: str | None = None,
) -> list[OptionChainRow]:
    async with AsyncClient() as client:
        return await client.options_chain(symbol, expiration=expiration, root=root)


async def option_series(symbol: str | Symbol) -> list[OptionSeries]:
    async with AsyncClient() as client:
        return await client.option_series(symbol)


async def options_info(symbol: str | Symbol) -> list[OptionSeries]:
    return await option_series(symbol)


async def options_series(symbol: str | Symbol) -> list[OptionSeries]:
    return await option_series(symbol)


async def history(symbol: str | Symbol, **kwargs: Any) -> list[Candle]:
    async with AsyncClient() as client:
        return await client.history(symbol, **kwargs)


async def news(symbol: str | Symbol, **kwargs: Any) -> list[NewsArticle]:
    async with AsyncClient() as client:
        return await client.news(symbol, **kwargs)


async def news_markdown(symbol: str | Symbol, **kwargs: Any) -> str:
    async with AsyncClient() as client:
        return await client.news_markdown(symbol, **kwargs)


async def research(symbol: str | Symbol, section: str) -> ResearchData:
    async with AsyncClient() as client:
        return await client.research(symbol, section)


async def bonds(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "bonds")


async def etfs(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "etfs")


async def documents(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "documents")


async def docs(symbol: str | Symbol) -> ResearchData:
    return await documents(symbol)


async def holdings(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "holdings")


async def ideas(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "ideas")


async def financials(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "financials")


async def forecast(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "forecast")


async def technicals(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "technicals")


async def profile(symbol: str | Symbol) -> ResearchData:
    return await research(symbol, "profile")


async def corporate_calendar(category: str, **kwargs: Any) -> list[CalendarEvent]:
    async with AsyncClient() as client:
        return await client.corporate_calendar(category, **kwargs)


async def earnings(**kwargs: Any) -> list[CalendarEvent]:
    return await corporate_calendar("earnings", **kwargs)


async def revenue(**kwargs: Any) -> list[CalendarEvent]:
    return await corporate_calendar("revenue", **kwargs)


async def dividends(**kwargs: Any) -> list[CalendarEvent]:
    return await corporate_calendar("dividends", **kwargs)


async def ipo(**kwargs: Any) -> list[CalendarEvent]:
    return await corporate_calendar("ipo", **kwargs)


async def economic_calendar(
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    countries: list[str] | None = None,
    importance: int | list[int] | None = None,
) -> list[CalendarEvent]:
    async with AsyncClient() as client:
        return await client.economic_calendar(
            from_date=from_date,
            to_date=to_date,
            countries=countries,
            importance=importance,
        )


async def calendar(
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    countries: list[str] | None = None,
    importance: int | list[int] | None = None,
) -> list[CalendarEvent]:
    return await economic_calendar(
        from_date=from_date,
        to_date=to_date,
        countries=countries,
        importance=importance,
    )


__all__ = [
    "AsyncClient",
    "bonds",
    "calendar",
    "corporate_calendar",
    "dividends",
    "docs",
    "documents",
    "earnings",
    "economic_calendar",
    "etfs",
    "financials",
    "forecast",
    "history",
    "holdings",
    "ideas",
    "ipo",
    "news",
    "news_markdown",
    "option_series",
    "options_chain",
    "options_info",
    "options_series",
    "profile",
    "quote",
    "quotes",
    "research",
    "revenue",
    "screener",
    "search",
    "stream_quotes",
    "technicals",
]
