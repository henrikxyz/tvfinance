"""High-level asynchronous and synchronous clients."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Coroutine
from datetime import datetime, timedelta, timezone
from typing import Any, TypeVar

from tvfinance.core.cache import MemoryResponseCache
from tvfinance.core.exceptions import ConfigurationError, RequestTimeoutError
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

    async def stream_quotes(self, symbols: list[str | Symbol]) -> AsyncIterator[Quote]:
        async for quote in self.provider.stream_quotes(symbols):
            yield quote

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
        expiration: int | None = None,
        root: str | None = None,
    ) -> list[OptionChainRow]:
        if expiration is None or root is None:
            series = await self.option_series(symbol)
            if not series:
                return []
            selected = next(
                (item for item in series if root is None or item.root == root),
                series[0],
            )
            expiration = expiration or selected.expiration
            root = root or selected.root
        return await self.provider.options_chain(
            symbol, expiration=expiration, root=root
        )

    async def option_series(self, symbol: str | Symbol) -> list[OptionSeries]:
        return await self.provider.option_series(symbol)

    async def history(
        self,
        symbol: str | Symbol,
        *,
        resolution: str = "1D",
        count: int | str | None = None,
        adjustment: str = "splits",
    ) -> list[Candle]:
        return await self.provider.history(
            symbol, resolution=resolution, count=count, adjustment=adjustment
        )

    async def news(
        self,
        symbol: str | Symbol,
        *,
        limit: int = 10,
        language: str | None = None,
        fetch_body: bool = False,
    ) -> list[NewsArticle]:
        return await self.provider.news(
            symbol, limit=limit, language=language, fetch_body=fetch_body
        )

    async def news_markdown(
        self, symbol: str | Symbol, *, limit: int = 10, language: str | None = None
    ) -> str:
        articles = await self.news(
            symbol, limit=limit, language=language, fetch_body=True
        )
        return "\n\n---\n\n".join(article.to_markdown() for article in articles)

    async def research(self, symbol: str | Symbol, section: str) -> ResearchData:
        return await self.provider.research(symbol, section)

    async def corporate_calendar(
        self,
        category: str,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 100,
    ) -> list[CalendarEvent]:
        start, end = _date_range(from_date, to_date)
        return await self.provider.corporate_calendar(
            category, from_date=start, to_date=end, limit=limit
        )

    async def economic_calendar(
        self,
        *,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        countries: list[str] | None = None,
        importance: int | list[int] | None = None,
    ) -> list[CalendarEvent]:
        start, end = _date_range(from_date, to_date)
        events = await self.provider.economic_calendar(
            from_date=start,
            to_date=end,
            countries=countries,
        )
        if importance is None:
            return events
        selected = {importance} if isinstance(importance, int) else set(importance)
        return [event for event in events if event.importance in selected]

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

    def _run(self, operation: Callable[[AsyncClient], Coroutine[Any, Any, T]]) -> T:
        async def scoped() -> T:
            async with await self._client() as client:
                return await operation(client)

        return run_sync(scoped)

    def search(self, query: str) -> list[SymbolSearchResult]:
        return self._run(lambda client: client.search(query))

    def quote(self, symbol: str | Symbol) -> Quote:
        return self._run(lambda client: client.quote(symbol))

    def quotes(self, symbols: list[str | Symbol]) -> dict[str, Quote | None]:
        return self._run(lambda client: client.quotes(symbols))

    def screener(self, **kwargs: Any) -> list[ScreenerRow]:
        return self._run(lambda client: client.screener(**kwargs))

    def options_chain(
        self,
        symbol: str | Symbol,
        *,
        expiration: int | None = None,
        root: str | None = None,
    ) -> list[OptionChainRow]:
        return self._run(
            lambda client: client.options_chain(
                symbol, expiration=expiration, root=root
            )
        )

    def option_series(self, symbol: str | Symbol) -> list[OptionSeries]:
        return self._run(lambda client: client.option_series(symbol))

    def history(self, symbol: str | Symbol, **kwargs: Any) -> list[Candle]:
        return self._run(lambda client: client.history(symbol, **kwargs))

    def news(self, symbol: str | Symbol, **kwargs: Any) -> list[NewsArticle]:
        return self._run(lambda client: client.news(symbol, **kwargs))

    def news_markdown(self, symbol: str | Symbol, **kwargs: Any) -> str:
        return self._run(lambda client: client.news_markdown(symbol, **kwargs))

    def research(self, symbol: str | Symbol, section: str) -> ResearchData:
        return self._run(lambda client: client.research(symbol, section))

    def corporate_calendar(self, category: str, **kwargs: Any) -> list[CalendarEvent]:
        return self._run(lambda client: client.corporate_calendar(category, **kwargs))

    def economic_calendar(self, **kwargs: Any) -> list[CalendarEvent]:
        return self._run(lambda client: client.economic_calendar(**kwargs))


def _date_range(
    from_date: datetime | None, to_date: datetime | None
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = from_date or now - timedelta(days=1)
    end = to_date or now + timedelta(days=7)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return start, end
