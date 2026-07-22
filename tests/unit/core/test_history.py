from __future__ import annotations

import json

import pytest

from tvfinance.core.exceptions import (
    ProtocolError,
    RequestTimeoutError,
    ValidationError,
)
from tvfinance.core.history import (
    _candles_from_update,
    _number,
    fetch_history,
    parse_timeframe,
)
from tvfinance.core.models import Symbol
from tvfinance.core.types import JsonValue
from tvfinance.core.websocket import encode_frame


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


def method(name: str, params: object) -> str:
    return encode_frame(json.dumps({"m": name, "p": params}))


def test_parse_timeframe() -> None:
    assert parse_timeframe("1D", None).count == 300
    assert parse_timeframe(" 1W ", "42").count == 42
    assert parse_timeframe("1", "max").count == 50_000
    assert parse_timeframe("1", 80_000).count == 50_000
    with pytest.raises(ValidationError):
        parse_timeframe("", 1)
    with pytest.raises(ValidationError):
        parse_timeframe("1D", "bad")
    with pytest.raises(ValidationError):
        parse_timeframe("1D", 0)


@pytest.mark.asyncio
async def test_fetch_history_collects_series_and_echoes_heartbeat() -> None:
    update = method(
        "timescale_update",
        [
            "session",
            {
                "s1": {
                    "s": [
                        {"v": [2, 2, 3, 1, 2.5, 20]},
                        {"v": [1, 1, 2, 0.5, 1.5, None]},
                    ]
                }
            },
        ],
    )
    socket = FakeSocket(["~h~1", update + method("series_completed", [])])
    candles = await fetch_history(socket, Symbol("NASDAQ", "AAPL"), count=2)
    assert [item.timestamp.timestamp() for item in candles] == [1, 2]
    assert candles[0].volume is None
    assert len(socket.sent) == 7
    assert socket.sent[6] == "~h~1"


@pytest.mark.asyncio
async def test_fetch_history_protocol_error() -> None:
    socket = FakeSocket([method("critical_error", [])])
    with pytest.raises(ProtocolError):
        await fetch_history(socket, Symbol("X", "Y"))


@pytest.mark.asyncio
async def test_fetch_history_timeout_and_ignored_message() -> None:
    symbol = Symbol("X", "Y")
    with pytest.raises(RequestTimeoutError):
        await fetch_history(FakeSocket([]), symbol, timeout=0)
    socket = FakeSocket([method("noop", []), method("series_completed", [])])
    assert await fetch_history(socket, symbol) == []


def test_candle_parser_ignores_malformed_rows() -> None:
    symbol = Symbol("X", "Y")
    params: list[JsonValue] = [
        "session",
        {
            "invalid": 1,
            "invalid_series": {"s": "bad"},
            "rows": {
                "s": [
                    {},
                    {"v": "bad"},
                    {"v": [1]},
                    {"v": ["bad", 1, 2, 3, 4]},
                ]
            },
        },
    ]
    assert _candles_from_update(symbol, params) == {}
    assert _candles_from_update(symbol, []) == {}


@pytest.mark.parametrize("value", [None, True, [], {}])
def test_number_rejects_non_numeric_values(value: object) -> None:
    with pytest.raises(ValueError):
        _number(value)  # type: ignore[arg-type]
