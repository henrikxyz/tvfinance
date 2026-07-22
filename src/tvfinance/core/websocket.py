"""TradingView-compatible text message framing helpers."""

from __future__ import annotations

import json
from typing import Any

from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException

from tvfinance.core.exceptions import ProtocolError, TransportError
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


class CurlWebSocket:
    """Adapt curl-cffi WebSockets to the provider-neutral contract."""

    def __init__(self, session: Any, socket: Any) -> None:
        self._session = session
        self._socket = socket
        self._closed = False

    @classmethod
    async def open(cls, url: str, *, headers: dict[str, str]) -> CurlWebSocket:
        session: Any = requests.AsyncSession(impersonate="chrome")
        try:
            socket = await session.ws_connect(url, headers=headers)
        except RequestException as exc:
            await session.close()
            raise TransportError(
                "WebSocket connection failed", retryable=True, context={"url": url}
            ) from exc
        return cls(session, socket)

    async def send_text(self, message: str) -> None:
        try:
            await self._socket.send_str(message)
        except RequestException as exc:
            raise TransportError("WebSocket send failed", retryable=True) from exc

    async def receive_text(self, *, timeout: float) -> str:
        try:
            return str(await self._socket.recv_str(timeout=timeout))
        except TimeoutError as exc:
            from tvfinance.core.exceptions import RequestTimeoutError

            raise RequestTimeoutError("WebSocket receive timed out") from exc
        except RequestException as exc:
            raise TransportError("WebSocket receive failed", retryable=True) from exc

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._socket.close()
            await self._session.close()


def decode_methods(buffer: str) -> tuple[list[dict[str, JsonValue]], str]:
    """Decode framed JSON method messages, ignoring non-object payloads."""
    payloads, remainder = decode_frames(buffer)
    methods: list[dict[str, JsonValue]] = []
    for payload in payloads:
        if is_heartbeat(payload):
            continue
        try:
            value = json.loads(payload)
        except ValueError as exc:
            raise ProtocolError("WebSocket payload is invalid JSON") from exc
        if isinstance(value, dict):
            methods.append(value)
    return methods, remainder
