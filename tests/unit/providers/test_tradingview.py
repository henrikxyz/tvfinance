from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, cast

import pytest

from tvfinance.core import (
    AsyncClientSession,
    ClientSettings,
    HttpRequest,
    HttpResponse,
    Locale,
    ParseError,
    RateLimitError,
    RequestTimeoutError,
    TransportError,
)
from tvfinance.core.exceptions import ProtocolError
from tvfinance.core.websocket import encode_frame
from tvfinance.providers import TradingViewProvider
from tvfinance.providers.tradingview import _option_series


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


class FakeSocket:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.sent: list[str] = []
        self.closed = 0

    async def send_text(self, message: str) -> None:
        self.sent.append(message)

    async def receive_text(self, *, timeout: float) -> str:
        if not self.responses:
            raise RequestTimeoutError()
        return self.responses.pop(0)

    async def close(self) -> None:
        self.closed += 1


def framed(method: str, params: object) -> str:
    return encode_frame(json.dumps({"m": method, "p": params}))


@pytest.mark.asyncio
async def test_provider_history_and_option_series(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, _ = provider()
    history_socket = FakeSocket(
        [
            framed(
                "timescale_update",
                ["x", {"s": {"s": [{"v": [1, 1, 2, 0, 1.5, 9]}]}}],
            )
            + framed("series_completed", [])
        ]
    )
    option_socket = FakeSocket(
        [
            framed("noop", [])
            + framed("qsd", [])
            + framed("qsd", ["x", {"v": "bad"}])
            + framed("qsd", ["x", {"v": {}}]),
            framed(
                "qsd",
                [
                    "x",
                    {
                        "v": {
                            "options-info": {
                                "series": [
                                    {"root": "AAPL", "expiration": 20261218},
                                    {"name": "AAPL", "expirations": [20270115]},
                                ]
                            }
                        }
                    },
                ],
            ),
        ]
    )
    sockets = [history_socket, option_socket]

    async def open_socket(url: str, *, headers: dict[str, str]) -> FakeSocket:
        return sockets.pop(0)

    monkeypatch.setattr(api.session, "open_websocket", open_socket)
    candles = await api.history("NASDAQ:AAPL", count=1)
    assert candles[0].close == 1.5
    assert history_socket.closed == 1
    series = await api.option_series("NASDAQ:AAPL")
    assert [(item.root, item.expiration) for item in series] == [
        ("AAPL", 20261218),
        ("AAPL", 20270115),
    ]
    assert option_socket.closed == 1


@pytest.mark.asyncio
async def test_provider_stream_quotes(monkeypatch: pytest.MonkeyPatch) -> None:
    api, _ = provider()
    socket = FakeSocket(
        [
            "~h~1",
            framed("noop", [])
            + framed("qsd", [])
            + framed("qsd", ["x", {"n": "NASDAQ:AAPL", "v": "bad"}]),
            framed(
                "qsd",
                [
                    "x",
                    {
                        "n": "NASDAQ:AAPL",
                        "v": {
                            "lp": 200,
                            "ch": 2,
                            "chp": 1,
                            "volume": 10,
                            "bid": 199,
                            "ask": 201,
                            "currency_code": "USD",
                            "rtc": 1,
                        },
                    },
                ],
            ),
        ]
    )

    async def open_socket(url: str, *, headers: dict[str, str]) -> FakeSocket:
        return socket

    monkeypatch.setattr(api.session, "open_websocket", open_socket)
    stream = api.stream_quotes(["NASDAQ:AAPL"])
    quote = await anext(stream)
    assert quote.last == 200
    assert quote.currency == "USD"
    await cast(Any, stream).aclose()
    assert "~h~1" in socket.sent
    assert socket.closed == 1


@pytest.mark.asyncio
async def test_provider_option_series_timeout_and_unknown_research(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, _ = provider()
    socket = FakeSocket([framed("qsd", ["x", {"v": {}}])])

    async def open_socket(url: str, *, headers: dict[str, str]) -> FakeSocket:
        return socket

    monkeypatch.setattr(api.session, "open_websocket", open_socket)
    object.__setattr__(api.session.settings, "timeout", 0.0)
    with pytest.raises(TransportError):
        await api.option_series("NASDAQ:AAPL")
    with pytest.raises(ProtocolError):
        await api.research("NASDAQ:AAPL", "unknown")


@pytest.mark.asyncio
async def test_provider_research_and_news_body() -> None:
    markup = (
        b"<html><table><tr><th>Name</th></tr><tr><td>Apple</td></tr></table></html>"
    )
    api, _ = provider(HttpResponse(200, markup))
    research_result = await api.research("NASDAQ:AAPL", "profile")
    assert research_result.records[0]["name"] == "Apple"

    payload = (
        b'{"items":[{"id":"n1","title":"Title","published":1,"storyPath":"/story"}]}'
    )
    article = b"<article><p>Article body</p></article>"
    api, _ = provider(HttpResponse(200, payload), HttpResponse(200, article))
    articles = await api.news("NASDAQ:AAPL", fetch_body=True)
    assert articles[0].body_markdown == "Article body"

    api, _ = provider(HttpResponse(500, b""))
    with pytest.raises(TransportError):
        await api._text("https://example.test")
    api, _ = provider(HttpResponse(200, b"\xff"))
    with pytest.raises(ParseError):
        await api._text("https://example.test")

    api, _ = provider(HttpResponse(200, payload), HttpResponse(500, b""))
    articles = await api.news("NASDAQ:AAPL", fetch_body=True)
    assert articles[0].body_markdown is None


@pytest.mark.asyncio
async def test_provider_corporate_calendars() -> None:
    rows = '{"data":[{"s":"NASDAQ:AAPL","d":["Apple","Apple Inc",1,2,3,4,5,6]}]}'
    api, transport = provider(*(response(rows) for _ in range(4)))
    start = datetime.fromtimestamp(0, tz=timezone.utc)
    end = datetime.fromtimestamp(10, tz=timezone.utc)
    for category in ("earnings", "revenue", "dividends", "ipo"):
        events = await api.corporate_calendar(
            category, from_date=start, to_date=end, limit=1
        )
        assert events[0].category == category
    assert len(transport.requests) == 4
    with pytest.raises(ProtocolError):
        await api.corporate_calendar("unknown", from_date=start, to_date=end)

    api, _ = provider(response('{"data":[{"s":"NASDAQ:AAPL","d":[null]}]}'))
    assert (
        await api.corporate_calendar("ipo", from_date=start, to_date=end, limit=1) == []
    )


def test_option_series_ignores_rootless_scalars() -> None:
    assert _option_series(20261218) == []
