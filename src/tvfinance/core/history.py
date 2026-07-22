"""Historical series protocol parsing and request orchestration."""

from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from tvfinance.core.contracts import AsyncWebSocket
from tvfinance.core.exceptions import (
    ProtocolError,
    RequestTimeoutError,
    ValidationError,
)
from tvfinance.core.models import Candle, Symbol
from tvfinance.core.types import JsonValue
from tvfinance.core.websocket import decode_methods, encode_method, is_heartbeat


@dataclass(frozen=True, slots=True)
class Timeframe:
    resolution: str
    count: int


def parse_timeframe(resolution: str, count: int | str | None) -> Timeframe:
    value = resolution.strip()
    if not value:
        raise ValidationError("resolution cannot be empty")
    if isinstance(count, str):
        if count.lower() == "max":
            count = 50_000
        elif count.isdigit():
            count = int(count)
        else:
            raise ValidationError("count must be a positive integer or 'max'")
    resolved_count = 300 if count is None else count
    if resolved_count <= 0:
        raise ValidationError("count must be greater than zero")
    return Timeframe(value, min(resolved_count, 50_000))


async def fetch_history(
    socket: AsyncWebSocket,
    symbol: Symbol,
    *,
    resolution: str = "1D",
    count: int | str | None = None,
    adjustment: str = "splits",
    timeout: float = 30.0,
) -> list[Candle]:
    """Fetch a complete chart series over an open WebSocket."""
    timeframe = parse_timeframe(resolution, count)
    chart_session = f"cs_{secrets.token_hex(6)}"
    symbol_payload = json.dumps(
        {"adjustment": adjustment, "symbol": symbol.ticker}, separators=(",", ":")
    )
    calls: list[tuple[str, list[JsonValue]]] = [
        ("set_auth_token", ["unauthorized_user_token"]),
        ("set_locale", ["en", "US"]),
        ("chart_create_session", [chart_session, ""]),
        ("switch_timezone", [chart_session, "Etc/UTC"]),
        ("resolve_symbol", [chart_session, "symbol_1", f"={symbol_payload}"]),
        (
            "create_series",
            [
                chart_session,
                "series_1",
                "s1",
                "symbol_1",
                timeframe.resolution,
                timeframe.count,
                "",
            ],
        ),
    ]
    for method, params in calls:
        await socket.send_text(encode_method(method, params))

    deadline = time.monotonic() + timeout
    buffer = ""
    candles: dict[int, Candle] = {}
    while time.monotonic() < deadline:
        chunk = await socket.receive_text(timeout=max(0.1, deadline - time.monotonic()))
        if is_heartbeat(chunk):
            await socket.send_text(chunk)
            continue
        buffer += chunk
        messages, buffer = decode_methods(buffer)
        for message in messages:
            msg_method = message.get("m")
            msg_params = message.get("p")
            if msg_method == "critical_error":
                raise ProtocolError("Provider rejected historical series request")
            if msg_method == "timescale_update" and isinstance(msg_params, list):
                candles.update(_candles_from_update(symbol, msg_params))
            if msg_method == "series_completed":
                return [candles[key] for key in sorted(candles)]
    raise RequestTimeoutError(
        "Historical series timed out", context={"symbol": symbol.ticker}
    )


def _candles_from_update(symbol: Symbol, params: list[JsonValue]) -> dict[int, Candle]:
    if len(params) < 2 or not isinstance(params[1], dict):
        return {}
    result: dict[int, Candle] = {}
    for series in params[1].values():
        if not isinstance(series, dict):
            continue
        raw_series = series.get("s")
        if not isinstance(raw_series, list):
            continue
        for raw in raw_series:
            if not isinstance(raw, dict) or not isinstance(raw.get("v"), list):
                continue
            values = raw["v"]
            assert isinstance(values, list)
            if len(values) < 5:
                continue
            try:
                timestamp = int(_number(values[0]))
                result[timestamp] = Candle(
                    symbol,
                    datetime.fromtimestamp(timestamp, tz=timezone.utc),
                    _number(values[1]),
                    _number(values[2]),
                    _number(values[3]),
                    _number(values[4]),
                    _number(values[5])
                    if len(values) > 5 and values[5] is not None
                    else None,
                )
            except (TypeError, ValueError, OSError):
                continue
    return result


def _number(value: JsonValue) -> float:
    if isinstance(value, bool | list | dict) or value is None:
        raise ValueError("not numeric")
    return float(value)
