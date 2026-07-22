from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, cast

import pytest

from tvfinance.client import AsyncClient, Client, run_sync
from tvfinance.core import (
    AsyncClientSession,
    ConfigurationError,
    HttpRequest,
    HttpResponse,
    RequestTimeoutError,
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
