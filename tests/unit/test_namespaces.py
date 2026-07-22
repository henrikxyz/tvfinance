from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import pytest

from tvfinance import aio, api


class FakeAsyncClient:
    async def __aenter__(self) -> FakeAsyncClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def search(self, query: str) -> Any:
        return query

    async def quote(self, symbol: object) -> Any:
        return symbol

    async def quotes(self, symbols: object) -> Any:
        return symbols

    async def screener(self, **kwargs: Any) -> Any:
        return kwargs

    async def options_chain(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    async def news(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    async def economic_calendar(self, **kwargs: Any) -> Any:
        return kwargs


class FakeClient:
    def search(self, query: str) -> Any:
        return query

    def quote(self, symbol: object) -> Any:
        return symbol

    def quotes(self, symbols: object) -> Any:
        return symbols

    def screener(self, **kwargs: Any) -> Any:
        return kwargs

    def options_chain(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    def news(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    def economic_calendar(self, **kwargs: Any) -> Any:
        return kwargs


@pytest.mark.asyncio
async def test_async_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aio, "AsyncClient", FakeAsyncClient)
    moment = datetime.now(timezone.utc)
    async_api = cast(Any, aio)
    assert await async_api.search("Apple") == "Apple"
    assert await async_api.quote("X:Y") == "X:Y"
    assert await async_api.quotes(["X:Y"]) == ["X:Y"]
    assert await async_api.screener(limit=1) == {"limit": 1}
    assert (await async_api.options_chain("X:Y", expiration=1, root="Y"))[0] == "X:Y"
    assert (await async_api.news("X:Y", limit=1))[0] == "X:Y"
    assert (await async_api.economic_calendar(from_date=moment, to_date=moment))[
        "from_date"
    ] == moment


def test_sync_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "Client", FakeClient)
    moment = datetime.now(timezone.utc)
    sync_api = cast(Any, api)
    assert sync_api.search("Apple") == "Apple"
    assert sync_api.quote("X:Y") == "X:Y"
    assert sync_api.quotes(["X:Y"]) == ["X:Y"]
    assert sync_api.screener(limit=1) == {"limit": 1}
    assert sync_api.options_chain("X:Y", expiration=1, root="Y")[0] == "X:Y"
    assert sync_api.news("X:Y", limit=1)[0] == "X:Y"
    assert (
        sync_api.economic_calendar(from_date=moment, to_date=moment)["to_date"]
        == moment
    )
