from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import pytest

from tvfinance import aio, api
from tvfinance.core.models import NewsArticle, Symbol
from tvfinance.ticker import AsyncTicker, AsyncTickers, Ticker, Tickers


class FakeClient:
    def option_series(self, symbol: object) -> Any:
        return symbol

    def history(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    def news_markdown(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    def research(self, symbol: object, section: str) -> Any:
        return symbol, section

    def corporate_calendar(self, category: str, **kwargs: Any) -> Any:
        return category, kwargs


class FakeAsyncClient:
    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def option_series(self, symbol: object) -> Any:
        return symbol

    async def history(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    async def news_markdown(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    async def research(self, symbol: object, section: str) -> Any:
        return symbol, section

    async def corporate_calendar(self, category: str, **kwargs: Any) -> Any:
        return category, kwargs

    async def stream_quotes(self, symbols: object) -> Any:
        yield symbols


def test_sync_extended_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "Client", FakeClient)
    sync_api = cast(Any, api)
    assert str(sync_api.option_series("X:Y")) == "X:Y"
    assert sync_api.history("X:Y", count=2)[1] == {"count": 2}
    assert sync_api.news_markdown("X:Y", limit=1)[1] == {"limit": 1}
    assert sync_api.research("X:Y", "profile")[1] == "profile"
    assert str(sync_api.options_info("X:Y")) == "X:Y"
    assert str(sync_api.options_series("X:Y")) == "X:Y"
    assert sync_api.docs("X:Y")[1] == "documents"
    monkeypatch.setattr(api, "economic_calendar", lambda **kwargs: kwargs)
    assert sync_api.calendar(importance=1)["importance"] == 1
    functions = [
        api.bonds,
        api.etfs,
        api.documents,
        api.holdings,
        api.ideas,
        api.financials,
        api.forecast,
        api.technicals,
        api.profile,
    ]
    assert [cast(Any, function("X:Y"))[1] for function in functions] == [
        "bonds",
        "etfs",
        "documents",
        "holdings",
        "ideas",
        "financials",
        "forecast",
        "technicals",
        "profile",
    ]
    calendar_functions = [api.earnings, api.revenue, api.dividends, api.ipo]
    assert [cast(Any, function(limit=1))[0] for function in calendar_functions] == [
        "earnings",
        "revenue",
        "dividends",
        "ipo",
    ]


@pytest.mark.asyncio
async def test_async_extended_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aio, "AsyncClient", FakeAsyncClient)
    async_api = cast(Any, aio)
    assert str(await async_api.option_series("X:Y")) == "X:Y"
    assert (await async_api.history("X:Y", count=2))[1] == {"count": 2}
    assert (await async_api.news_markdown("X:Y", limit=1))[1] == {"limit": 1}
    assert str(await async_api.options_info("X:Y")) == "X:Y"
    assert str(await async_api.options_series("X:Y")) == "X:Y"
    assert (await async_api.docs("X:Y"))[1] == "documents"
    stream = async_api.stream_quotes(["X:Y"])
    assert [item async for item in stream] == [["X:Y"]]
    functions = [
        aio.bonds,
        aio.etfs,
        aio.documents,
        aio.holdings,
        aio.ideas,
        aio.financials,
        aio.forecast,
        aio.technicals,
        aio.profile,
    ]
    results = [await function("X:Y") for function in functions]
    assert [cast(Any, item)[1] for item in results] == [
        "bonds",
        "etfs",
        "documents",
        "holdings",
        "ideas",
        "financials",
        "forecast",
        "technicals",
        "profile",
    ]
    calendars = [aio.earnings, aio.revenue, aio.dividends, aio.ipo]
    calendar_results = [await function(limit=1) for function in calendars]
    assert [cast(Any, item)[0] for item in calendar_results] == [
        "earnings",
        "revenue",
        "dividends",
        "ipo",
    ]

    async def fake_economic(**kwargs: Any) -> Any:
        return kwargs

    monkeypatch.setattr(aio, "economic_calendar", fake_economic)
    assert (await async_api.calendar(importance=1))["importance"] == 1


class TickerClient(FakeClient):
    def quote(self, symbol: object) -> Any:
        return symbol

    def news(self, symbol: object, **kwargs: Any) -> Any:
        return (symbol, kwargs) if kwargs else [str(symbol)]

    def options_chain(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    def quotes(self, symbols: object) -> Any:
        return {"quotes": symbols}


def test_ticker_extended_methods() -> None:
    ticker = Ticker("X:Y", client=cast(Any, TickerClient()))
    untyped = cast(Any, ticker)
    assert untyped.history(count=1)[1] == {"count": 1}
    assert str(untyped.option_series()) == "X:Y"
    assert str(untyped.options_info()) == "X:Y"
    assert str(untyped.options_series()) == "X:Y"
    assert untyped.news_markdown(limit=1)[1]["limit"] == 1
    assert [
        cast(Any, ticker.bonds())[1],
        cast(Any, ticker.etfs())[1],
        cast(Any, ticker.documents())[1],
        cast(Any, ticker.docs())[1],
        cast(Any, ticker.holdings())[1],
        cast(Any, ticker.ideas())[1],
        cast(Any, ticker.financials())[1],
        cast(Any, ticker.forecast())[1],
        cast(Any, ticker.technicals())[1],
        cast(Any, ticker.profile())[1],
    ] == [
        "bonds",
        "etfs",
        "documents",
        "documents",
        "holdings",
        "ideas",
        "financials",
        "forecast",
        "technicals",
        "profile",
    ]
    tickers = Tickers(["X:Y", "X:Z"], client=cast(Any, TickerClient()))
    assert list(cast(Any, tickers.quotes())["quotes"]) == [
        Symbol("X", "Y"),
        Symbol("X", "Z"),
    ]
    assert set(tickers.history(count=1)) == {"X:Y", "X:Z"}
    assert cast(Any, tickers.news())["X:Y"] == ["X:Y"]
    assert cast(Any, tickers.research("profile")["X:Z"])[1] == "profile"


class AsyncTickerClient(FakeAsyncClient):
    closed = 0

    async def quote(self, symbol: object) -> Any:
        return symbol

    async def news(self, symbol: object, **kwargs: Any) -> Any:
        return (symbol, kwargs) if kwargs else [str(symbol)]

    async def options_chain(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    async def close(self) -> None:
        self.closed += 1

    async def quotes(self, symbols: object) -> Any:
        return {"quotes": symbols}

    async def history(self, symbol: object, **kwargs: Any) -> Any:
        return (symbol, kwargs) if kwargs else [str(symbol)]

    async def research(self, symbol: object, section: str) -> Any:
        return str(symbol), section


@pytest.mark.asyncio
async def test_async_ticker_extended_methods() -> None:
    client = AsyncTickerClient()
    ticker = AsyncTicker("X:Y", client=cast(Any, client))
    untyped = cast(Any, ticker)
    assert str(await untyped.quote()) == "X:Y"
    assert await anext(untyped.stream()) == [Symbol("X", "Y")]
    assert (await untyped.history(count=1))[1]["count"] == 1
    assert (await untyped.news(limit=1))[1]["limit"] == 1
    assert (await untyped.news_markdown(limit=1))[1]["limit"] == 1
    assert str(await untyped.option_series()) == "X:Y"
    assert (await untyped.options_chain())[1]["root"] == "Y"
    assert (await untyped.research("profile"))[1] == "profile"
    async with ticker as entered:
        assert entered is ticker
    assert client.closed == 0


@pytest.mark.asyncio
async def test_owned_async_tickers_close(monkeypatch: pytest.MonkeyPatch) -> None:
    ticker_client = AsyncTickerClient()
    clients = iter([ticker_client, ticker_client])
    monkeypatch.setattr("tvfinance.ticker.AsyncClient", lambda: next(clients))
    ticker = AsyncTicker("X:Y")
    assert cast(Any, [item async for item in ticker.stream()]) == [[Symbol("X", "Y")]]
    await ticker.close()
    tickers = AsyncTickers(["X:Y"])
    await tickers.close()
    assert ticker_client.closed == 2

    tickers = AsyncTickers(["X:Y", "X:Z"], client=cast(Any, ticker_client))
    assert "quotes" in await tickers.quotes()
    assert cast(Any, await tickers.history())["X:Y"] == ["X:Y"]
    assert cast(Any, await tickers.news())["X:Z"] == ["X:Z"]
    assert cast(Any, (await tickers.research("profile"))["X:Y"])[1] == "profile"
    async with tickers as entered:
        assert entered is tickers
    assert ticker_client.closed == 2


def test_news_markdown_model() -> None:
    article = NewsArticle(
        "1",
        "Title",
        datetime(2026, 1, 1, tzinfo=timezone.utc),
        source="Wire",
        url="https://example.test",
        summary="Summary",
        body_markdown="Body",
        symbols=(Symbol("X", "Y"),),
    )
    rendered = article.to_markdown()
    assert "Source: Wire" in rendered
    assert "Symbols: X:Y" in rendered
    assert rendered.endswith("Body\n")
    minimal = NewsArticle("2", "Minimal", datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert minimal.to_markdown().endswith("+00:00\n")
