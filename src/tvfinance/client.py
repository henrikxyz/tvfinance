"""High-level asynchronous and synchronous clients."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any, TypeVar

from tvfinance.core.cache import MemoryResponseCache
from tvfinance.core.exceptions import ConfigurationError, RequestTimeoutError
from tvfinance.core.models import (
    CalendarEvent,
    NewsArticle,
    OptionChainRow,
    Quote,
    ScreenerRow,
    Symbol,
    SymbolSearchResult,
)
from tvfinance.core.session import AsyncClientSession
from tvfinance.core.settings import ClientSettings
from tvfinance.providers import TradingViewProvider

T = TypeVar("T")


class AsyncClient:
    """Reusable asynchronous client for all implemented domain operations."""

    def __init__(
        self,
        *,
        settings: ClientSettings | None = None,
        session: AsyncClientSession | None = None,
        cache: MemoryResponseCache | None = None,
    ) -> None:
        self._owns_session = session is None
        self.session = session or AsyncClientSession(settings=settings, cache=cache)
        self.provider = TradingViewProvider(self.session)

    async def search(self, query: str) -> list[SymbolSearchResult]:
        return await self.provider.search(query)

    async def quotes(self, symbols: list[str | Symbol]) -> dict[str, Quote | None]:
        return await self.provider.quotes(symbols)

    async def quote(self, symbol: str | Symbol) -> Quote:
        normalized = (
            str(symbol) if isinstance(symbol, Symbol) else symbol.strip().upper()
        )
        result = await self.quotes([symbol])
        quote = result.get(normalized)
        if quote is None:
            raise RequestTimeoutError(
                "Provider returned no quote",
                context={"symbol": normalized},
            )
        return quote

    async def screener(
        self,
        *,
        market: str = "america",
        columns: list[str] | None = None,
        limit: int = 50,
        sort_by: str = "market_cap_basic",
        sort_order: str = "desc",
    ) -> list[ScreenerRow]:
        return await self.provider.screener(
            market=market,
            columns=columns,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def options_chain(
        self,
        symbol: str | Symbol,
        *,
        expiration: int,
        root: str,
    ) -> list[OptionChainRow]:
        return await self.provider.options_chain(
            symbol, expiration=expiration, root=root
        )

    async def news(
        self,
        symbol: str | Symbol,
        *,
        limit: int = 10,
        language: str | None = None,
    ) -> list[NewsArticle]:
        return await self.provider.news(symbol, limit=limit, language=language)

    async def economic_calendar(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        countries: list[str] | None = None,
    ) -> list[CalendarEvent]:
        return await self.provider.economic_calendar(
            from_date=from_date,
            to_date=to_date,
            countries=countries,
        )

    async def close(self) -> None:
        if self._owns_session:
            await self.session.close()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        await self.close()


def run_sync(factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
    """Run one async operation unless already inside an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())
    raise ConfigurationError(
        "Synchronous API cannot run inside an event loop; use tvfinance.aio"
    )


class Client:
    """Synchronous facade that creates a scoped async client per operation."""

    def __init__(
        self,
        *,
        settings: ClientSettings | None = None,
        cache: MemoryResponseCache | None = None,
    ) -> None:
        self.settings = settings
        self.cache = cache

    async def _client(self) -> AsyncClient:
        return AsyncClient(settings=self.settings, cache=self.cache)

    def search(self, query: str) -> list[SymbolSearchResult]:
        async def operation() -> list[SymbolSearchResult]:
            async with await self._client() as client:
                return await client.search(query)

        return run_sync(operation)

    def quote(self, symbol: str | Symbol) -> Quote:
        async def operation() -> Quote:
            async with await self._client() as client:
                return await client.quote(symbol)

        return run_sync(operation)

    def quotes(self, symbols: list[str | Symbol]) -> dict[str, Quote | None]:
        async def operation() -> dict[str, Quote | None]:
            async with await self._client() as client:
                return await client.quotes(symbols)

        return run_sync(operation)

    def screener(self, **kwargs: Any) -> list[ScreenerRow]:
        async def operation() -> list[ScreenerRow]:
            async with await self._client() as client:
                return await client.screener(**kwargs)

        return run_sync(operation)

    def options_chain(
        self, symbol: str | Symbol, *, expiration: int, root: str
    ) -> list[OptionChainRow]:
        async def operation() -> list[OptionChainRow]:
            async with await self._client() as client:
                return await client.options_chain(
                    symbol, expiration=expiration, root=root
                )

        return run_sync(operation)

    def news(self, symbol: str | Symbol, **kwargs: Any) -> list[NewsArticle]:
        async def operation() -> list[NewsArticle]:
            async with await self._client() as client:
                return await client.news(symbol, **kwargs)

        return run_sync(operation)

    def economic_calendar(self, **kwargs: Any) -> list[CalendarEvent]:
        async def operation() -> list[CalendarEvent]:
            async with await self._client() as client:
                return await client.economic_calendar(**kwargs)

        return run_sync(operation)
