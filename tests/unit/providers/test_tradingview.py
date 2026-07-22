from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import cast

import pytest

from tvfinance.core import (
    AsyncClientSession,
    ClientSettings,
    HttpRequest,
    HttpResponse,
    Locale,
    ParseError,
    RateLimitError,
    TransportError,
)
from tvfinance.providers import TradingViewProvider


class FakeTransport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = responses
        self.requests: list[HttpRequest] = []

    async def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.responses.pop(0)

    async def close(self) -> None:
        return None


def response(data: str, status: int = 200) -> HttpResponse:
    return HttpResponse(status, data.encode())


def provider(*responses: HttpResponse) -> tuple[TradingViewProvider, FakeTransport]:
    transport = FakeTransport(list(responses))
    session = AsyncClientSession(
        settings=ClientSettings(locale=Locale("zh", "TW")), transport=transport
    )
    return TradingViewProvider(session), transport


@pytest.mark.asyncio
async def test_search_maps_typed_results_and_skips_incomplete_rows() -> None:
    api, transport = provider(
        response(
            '[{"exchange":"NASDAQ","symbol":"AAPL","description":"Apple",'
            '"type":"stock","currency_code":"USD","provider_id":"ice"},{}]'
        )
    )
    results = await api.search(" Apple ")
    assert results[0].symbol.ticker == "NASDAQ:AAPL"
    assert results[0].currency == "USD"
    assert transport.requests[0].headers["Accept-Language"] == "zh-TW,zh;q=0.9"
    assert await api.search("  ") == []


@pytest.mark.asyncio
async def test_quotes_maps_rows_and_preserves_missing_symbols() -> None:
    values = [200, 1.5, 3, 195, 202, 194, 2, 1000, "bad", 201, "USD"]
    api, _ = provider(
        response(
            '{"data":[{"s":"NASDAQ:AAPL","d":' + str(values).replace("'", '"') + "}]}"
        )
    )
    result = await api.quotes(["NASDAQ:AAPL", "NASDAQ:MSFT"])
    assert result["NASDAQ:AAPL"].last == 200  # type: ignore[union-attr]
    assert result["NASDAQ:AAPL"].currency == "USD"  # type: ignore[union-attr]
    assert result["NASDAQ:AAPL"].bid is None  # type: ignore[union-attr]
    assert result["NASDAQ:MSFT"] is None


@pytest.mark.asyncio
async def test_screener_maps_columns() -> None:
    api, _ = provider(response('{"data":[{"s":"NASDAQ:AAPL","d":[200,1]}]}'))
    rows = await api.screener(columns=["close", "change"], limit=1)
    assert rows[0].values == {"close": 200, "change": 1}


@pytest.mark.asyncio
async def test_option_chain_pairs_contracts() -> None:
    payload = (
        '{"fields":["strike","option-type","expiration","root","bid"],'
        '"symbols":['
        '{"s":"OPRA:AAPL1","f":[200,"call",20261218,"AAPL",2]},'
        '{"s":"OPRA:AAPL2","f":[200,"put",20261218,"AAPL",3]}]}'
    )
    api, _ = provider(response(payload))
    rows = await api.options_chain("NASDAQ:AAPL", expiration=20261218, root="AAPL")
    assert rows[0].call is not None
    assert rows[0].put is not None
    assert rows[0].call.bid == 2


@pytest.mark.asyncio
async def test_news_maps_provider_and_story() -> None:
    payload = (
        '{"items":[{"id":"n1","title":"Title","published":1,'
        '"provider":{"name":"Wire"},"storyPath":"/story",'
        '"description":"Summary"}]}'
    )
    api, transport = provider(response(payload))
    articles = await api.news("NASDAQ:AAPL", limit=1)
    assert articles[0].source == "Wire"
    assert articles[0].url == "https://www.tradingview.com/story"
    assert isinstance(transport.requests[0].params, list)


@pytest.mark.asyncio
async def test_economic_calendar_maps_values_and_country_filter() -> None:
    payload = (
        '{"result":[{"id":"e1","title":"CPI",'
        '"date":"2026-07-22T00:00:00Z","country":"US",'
        '"importance":1,"actual":2,"forecast":3,"previous":4}]}'
    )
    api, transport = provider(response(payload), response('{"result":[]}'))
    moment = datetime(2026, 7, 22, tzinfo=timezone.utc)
    events = await api.economic_calendar(
        from_date=moment, to_date=moment, countries=["US"]
    )
    assert events[0].title == "CPI"
    params = cast(Mapping[str, object], transport.requests[0].params)
    assert params["countries"] == "US"
    assert await api.economic_calendar(from_date=moment, to_date=moment) == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("item", "error"),
    [
        (response("{}", 429), RateLimitError),
        (response("{}", 403), TransportError),
        (response("not-json"), ParseError),
        (response("{}"), ParseError),
    ],
)
async def test_provider_errors(item: HttpResponse, error: type[Exception]) -> None:
    api, _ = provider(item)
    with pytest.raises(error):
        await api.search("Apple")


@pytest.mark.asyncio
async def test_provider_rejects_non_object_scanner_response() -> None:
    api, _ = provider(response("[]"))
    with pytest.raises(ParseError):
        await api.screener()
