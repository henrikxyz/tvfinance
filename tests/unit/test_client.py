from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, cast

import pytest

from tvfinance.client import AsyncClient, Client, _date_range, run_sync
from tvfinance.core import (
    AsyncClientSession,
    ConfigurationError,
    HttpRequest,
    HttpResponse,
    RequestTimeoutError,
)
from tvfinance.core.models import (
    CalendarEvent,
    Candle,
    NewsArticle,
    OptionSeries,
    Quote,
    ResearchData,
    Symbol,
)


class FakeTransport:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.closed = 0

    async def send(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse(200, self.responses.pop(0).encode())

    async def close(self) -> None:
        self.closed += 1


@pytest.mark.asyncio
async def test_async_client_operations_and_owned_session() -> None:
    responses = [
        '[{"exchange":"NASDAQ","symbol":"AAPL"}]',
        '{"data":[{"s":"NASDAQ:AAPL","d":[200]}]}',
        '{"data":[{"s":"NASDAQ:AAPL","d":[200]}]}',
        '{"data":[]}',
        '{"symbols":[]}',
        '{"items":[]}',
        '{"result":[]}',
    ]
    transport = FakeTransport(responses)
    session = AsyncClientSession(transport=transport)
    client = AsyncClient(session=session)
    assert (await client.search("Apple"))[0].symbol.name == "AAPL"
    assert (await client.quotes(["NASDAQ:AAPL"]))["NASDAQ:AAPL"] is not None
    assert (await client.quote("NASDAQ:AAPL")).last == 200
    assert await client.screener() == []
    assert (
        await client.options_chain("NASDAQ:AAPL", expiration=20261218, root="AAPL")
        == []
    )
    assert await client.news("NASDAQ:AAPL") == []
    moment = datetime.now(timezone.utc)
    assert await client.economic_calendar(from_date=moment, to_date=moment) == []
    async with client as entered:
        assert entered is client
    assert transport.closed == 0


@pytest.mark.asyncio
async def test_async_client_missing_quote() -> None:
    client = AsyncClient(
        session=AsyncClientSession(transport=FakeTransport(['{"data":[]}']))
    )
    with pytest.raises(RequestTimeoutError):
        await client.quote("NASDAQ:AAPL")


@pytest.mark.asyncio
async def test_async_client_closes_owned_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = FakeTransport([])
    session = AsyncClientSession(transport=transport)
    monkeypatch.setattr("tvfinance.client.AsyncClientSession", lambda **kwargs: session)
    client = AsyncClient()
    assert client._owns_session is True
    await client.close()
    assert transport.closed == 1


@pytest.mark.asyncio
async def test_run_sync_rejects_running_loop() -> None:
    with pytest.raises(ConfigurationError):
        run_sync(lambda: asyncio.sleep(0))


def test_sync_client_delegates_all_operations(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeAsyncClient:
        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def search(self, query: str) -> list[Any]:
            return [query]

        async def quote(self, symbol: object) -> Any:
            return symbol

        async def quotes(self, symbols: list[object]) -> Any:
            return symbols

        async def screener(self, **kwargs: Any) -> Any:
            return kwargs

        async def options_chain(self, symbol: object, **kwargs: Any) -> Any:
            return symbol, kwargs

        async def news(self, symbol: object, **kwargs: Any) -> Any:
            return symbol, kwargs

        async def economic_calendar(self, **kwargs: Any) -> Any:
            return kwargs

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

    async def fake_client(self: Client) -> Any:
        return FakeAsyncClient()

    monkeypatch.setattr(Client, "_client", fake_client)
    client = Client()
    untyped = cast(Any, client)
    assert untyped.search("x") == ["x"]
    assert untyped.quote("X:Y") == "X:Y"
    assert untyped.quotes(["X:Y"]) == ["X:Y"]
    assert untyped.screener(limit=1) == {"limit": 1}
    assert untyped.options_chain("X:Y", expiration=1, root="Y")[0] == "X:Y"
    assert untyped.news("X:Y", limit=1)[0] == "X:Y"
    assert untyped.economic_calendar(limit=1) == {"limit": 1}
    assert untyped.option_series("X:Y") == "X:Y"
    assert untyped.history("X:Y", count=1)[1]["count"] == 1
    assert untyped.news_markdown("X:Y", limit=1)[1]["limit"] == 1
    assert untyped.research("X:Y", "profile")[1] == "profile"
    assert untyped.corporate_calendar("ipo", limit=1)[0] == "ipo"


@pytest.mark.asyncio
async def test_async_client_extended_operations() -> None:
    symbol = Symbol("X", "Y")
    moment = datetime.now(timezone.utc)

    class FakeProvider:
        async def option_series(self, value: object) -> list[OptionSeries]:
            return [OptionSeries("Y", 20261218)]

        async def options_chain(self, value: object, **kwargs: Any) -> list[Any]:
            assert kwargs == {"expiration": 20261218, "root": "Y"}
            return []

        async def history(self, value: object, **kwargs: Any) -> list[Candle]:
            return [Candle(symbol, moment, 1, 2, 0, 1.5)]

        async def news(self, value: object, **kwargs: Any) -> list[NewsArticle]:
            return [NewsArticle("1", "Title", moment, body_markdown="Body")]

        async def research(self, value: object, section: str) -> ResearchData:
            return ResearchData(symbol, section)

        async def corporate_calendar(
            self, category: str, **kwargs: Any
        ) -> list[CalendarEvent]:
            assert kwargs["from_date"].tzinfo is not None
            return [CalendarEvent("1", category, moment, category)]

        async def economic_calendar(self, **kwargs: Any) -> list[CalendarEvent]:
            return [
                CalendarEvent("1", "Low", moment, "economic", importance=0),
                CalendarEvent("2", "High", moment, "economic", importance=1),
            ]

        async def stream_quotes(self, values: object) -> Any:
            yield Quote(symbol, last=1)

    client = AsyncClient(session=AsyncClientSession(transport=FakeTransport([])))
    client.provider = cast(Any, FakeProvider())
    assert await client.options_chain("X:Y") == []
    assert (await client.history("X:Y"))[0].close == 1.5
    assert (await client.news("X:Y", fetch_body=True))[0].title == "Title"
    assert (await client.news_markdown("X:Y")).endswith("Body\n")
    assert (await client.research("X:Y", "profile")).section == "profile"
    assert (await client.corporate_calendar("ipo"))[0].category == "ipo"
    events = await client.economic_calendar(importance=1)
    assert [event.title for event in events] == ["High"]
    assert [item.last async for item in client.stream_quotes(["X:Y"])] == [1]

    class EmptyOptions(FakeProvider):
        async def option_series(self, value: object) -> list[OptionSeries]:
            return []

    client.provider = cast(Any, EmptyOptions())
    assert await client.options_chain("X:Y") == []


@pytest.mark.asyncio
async def test_sync_client_creates_real_async_client() -> None:
    client = await Client()._client()
    assert isinstance(client, AsyncClient)
    await client.close()


def test_date_range_normalizes_naive_datetimes() -> None:
    start, end = _date_range(datetime(2026, 1, 1), datetime(2026, 1, 2))
    assert start.tzinfo is timezone.utc
    assert end.tzinfo is timezone.utc
