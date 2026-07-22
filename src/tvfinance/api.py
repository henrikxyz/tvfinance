"""Stable synchronous functional API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from tvfinance.client import Client
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


def search(query: str) -> list[SymbolSearchResult]:
    return Client().search(query)


def quote(symbol: str | Symbol) -> Quote:
    return Client().quote(symbol)


def quotes(symbols: list[str | Symbol]) -> dict[str, Quote | None]:
    return Client().quotes(symbols)


def screener(**kwargs: Any) -> list[ScreenerRow]:
    return Client().screener(**kwargs)


def options_chain(
    symbol: str | Symbol,
    *,
    expiration: int | None = None,
    root: str | None = None,
) -> list[OptionChainRow]:
    return Client().options_chain(symbol, expiration=expiration, root=root)


def option_series(symbol: str | Symbol) -> list[OptionSeries]:
    return Client().option_series(symbol)


def options_info(symbol: str | Symbol) -> list[OptionSeries]:
    return option_series(symbol)


def options_series(symbol: str | Symbol) -> list[OptionSeries]:
    return option_series(symbol)


def history(symbol: str | Symbol, **kwargs: Any) -> list[Candle]:
    return Client().history(symbol, **kwargs)


def news(symbol: str | Symbol, **kwargs: Any) -> list[NewsArticle]:
    return Client().news(symbol, **kwargs)


def news_markdown(symbol: str | Symbol, **kwargs: Any) -> str:
    return Client().news_markdown(symbol, **kwargs)


def research(symbol: str | Symbol, section: str) -> ResearchData:
    return Client().research(symbol, section)


def bonds(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "bonds")


def etfs(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "etfs")


def documents(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "documents")


def docs(symbol: str | Symbol) -> ResearchData:
    return documents(symbol)


def holdings(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "holdings")


def ideas(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "ideas")


def financials(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "financials")


def forecast(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "forecast")


def technicals(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "technicals")


def profile(symbol: str | Symbol) -> ResearchData:
    return research(symbol, "profile")


def corporate_calendar(category: str, **kwargs: Any) -> list[CalendarEvent]:
    return Client().corporate_calendar(category, **kwargs)


def earnings(**kwargs: Any) -> list[CalendarEvent]:
    return corporate_calendar("earnings", **kwargs)


def revenue(**kwargs: Any) -> list[CalendarEvent]:
    return corporate_calendar("revenue", **kwargs)


def dividends(**kwargs: Any) -> list[CalendarEvent]:
    return corporate_calendar("dividends", **kwargs)


def ipo(**kwargs: Any) -> list[CalendarEvent]:
    return corporate_calendar("ipo", **kwargs)


def economic_calendar(
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    countries: list[str] | None = None,
    importance: int | list[int] | None = None,
) -> list[CalendarEvent]:
    return Client().economic_calendar(
        from_date=from_date,
        to_date=to_date,
        countries=countries,
        importance=importance,
    )


def calendar(
    *,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    countries: list[str] | None = None,
    importance: int | list[int] | None = None,
) -> list[CalendarEvent]:
    return economic_calendar(
        from_date=from_date,
        to_date=to_date,
        countries=countries,
        importance=importance,
    )
