"""Object-oriented symbol facade."""

from __future__ import annotations

from typing import Any

from tvfinance.client import AsyncClient, Client
from tvfinance.core.models import (
    Candle,
    NewsArticle,
    OptionChainRow,
    OptionSeries,
    Quote,
    ResearchData,
    Symbol,
)
from tvfinance.core.validation import normalize_symbol


class Ticker:
    """Bind repeated operations to one validated symbol."""

    def __init__(self, symbol: str | Symbol, *, client: Client | None = None) -> None:
        self.symbol = normalize_symbol(symbol)
        self.client = client or Client()

    def quote(self) -> Quote:
        return self.client.quote(self.symbol)

    def news(
        self, *, limit: int = 10, language: str | None = None
    ) -> list[NewsArticle]:
        return self.client.news(self.symbol, limit=limit, language=language)

    def options_chain(
        self, *, expiration: int | None = None, root: str | None = None
    ) -> list[OptionChainRow]:
        return self.client.options_chain(
            self.symbol,
            expiration=expiration,
            root=root or self.symbol.name,
        )

    def option_series(self) -> list[OptionSeries]:
        return self.client.option_series(self.symbol)

    def history(self, **kwargs: Any) -> list[Candle]:
        return self.client.history(self.symbol, **kwargs)

    def news_markdown(self, *, limit: int = 10, language: str | None = None) -> str:
        return self.client.news_markdown(self.symbol, limit=limit, language=language)

    def research(self, section: str) -> ResearchData:
        return self.client.research(self.symbol, section)

    def bonds(self) -> ResearchData:
        return self.research("bonds")

    def etfs(self) -> ResearchData:
        return self.research("etfs")

    def documents(self) -> ResearchData:
        return self.research("documents")

    def holdings(self) -> ResearchData:
        return self.research("holdings")

    def ideas(self) -> ResearchData:
        return self.research("ideas")

    def financials(self) -> ResearchData:
        return self.research("financials")

    def forecast(self) -> ResearchData:
        return self.research("forecast")

    def technicals(self) -> ResearchData:
        return self.research("technicals")

    def profile(self) -> ResearchData:
        return self.research("profile")


class AsyncTicker:
    """Asynchronous object-oriented facade bound to one symbol."""

    def __init__(
        self, symbol: str | Symbol, *, client: AsyncClient | None = None
    ) -> None:
        self.symbol = normalize_symbol(symbol)
        self.client = client or AsyncClient()
        self._owns_client = client is None

    async def quote(self) -> Quote:
        return await self.client.quote(self.symbol)

    async def history(self, **kwargs: Any) -> list[Candle]:
        return await self.client.history(self.symbol, **kwargs)

    async def news(self, **kwargs: Any) -> list[NewsArticle]:
        return await self.client.news(self.symbol, **kwargs)

    async def news_markdown(self, **kwargs: Any) -> str:
        return await self.client.news_markdown(self.symbol, **kwargs)

    async def option_series(self) -> list[OptionSeries]:
        return await self.client.option_series(self.symbol)

    async def options_chain(
        self, *, expiration: int | None = None, root: str | None = None
    ) -> list[OptionChainRow]:
        return await self.client.options_chain(
            self.symbol, expiration=expiration, root=root or self.symbol.name
        )

    async def research(self, section: str) -> ResearchData:
        return await self.client.research(self.symbol, section)

    async def close(self) -> None:
        if self._owns_client:
            await self.client.close()

    async def __aenter__(self) -> AsyncTicker:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        await self.close()
