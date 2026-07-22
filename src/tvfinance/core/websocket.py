"""TradingView-compatible text message framing helpers."""

from __future__ import annotations

import json

from tvfinance.core.exceptions import ProtocolError
from tvfinance.core.types import JsonValue

_PREFIX = "~m~"


def encode_frame(payload: str) -> str:
    """Wrap one text payload in a length-prefixed frame."""
    return f"{_PREFIX}{len(payload.encode('utf-8'))}{_PREFIX}{payload}"


def encode_method(method: str, params: list[JsonValue]) -> str:
    """Encode one protocol method call."""
    return encode_frame(json.dumps({"m": method, "p": params}, separators=(",", ":")))


def decode_frames(buffer: str) -> tuple[list[str], str]:
    """Decode all complete frames and return any incomplete suffix."""
    messages: list[str] = []
    while buffer:
        if not buffer.startswith(_PREFIX):
            raise ProtocolError("WebSocket frame prefix is invalid")
        length_end = buffer.find(_PREFIX, len(_PREFIX))
        if length_end < 0:
            break
        raw_length = buffer[len(_PREFIX) : length_end]
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ProtocolError("WebSocket frame length is invalid") from exc
        payload_start = length_end + len(_PREFIX)
        payload_bytes = buffer[payload_start:].encode("utf-8")
        if len(payload_bytes) < length:
            break
        payload = payload_bytes[:length].decode("utf-8")
        consumed = payload_start + len(payload)
        messages.append(payload)
        buffer = buffer[consumed:]
    return messages, buffer


def is_heartbeat(message: str) -> bool:
    """Return whether a payload is a provider heartbeat."""
    return message.startswith("~h~")
