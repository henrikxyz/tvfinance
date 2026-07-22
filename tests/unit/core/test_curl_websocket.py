from __future__ import annotations

from typing import Any

import pytest
from curl_cffi.requests.exceptions import RequestException

from tvfinance.core.exceptions import ProtocolError, RequestTimeoutError, TransportError
from tvfinance.core.websocket import CurlWebSocket, decode_methods, encode_frame


class Socket:
    def __init__(self) -> None:
        self.closed = 0
        self.sent: list[str] = []
        self.value: object = "hello"

    async def send_str(self, value: str) -> None:
        if isinstance(self.value, Exception):
            raise self.value
        self.sent.append(value)

    async def recv_str(self, *, timeout: float) -> str:
        if isinstance(self.value, Exception):
            raise self.value
        return str(self.value)

    async def close(self) -> None:
        self.closed += 1


class Session:
    def __init__(self, socket: Socket | Exception) -> None:
        self.socket = socket
        self.closed = 0

    async def ws_connect(self, url: str, headers: object) -> Any:
        if isinstance(self.socket, Exception):
            raise self.socket
        return self.socket

    async def close(self) -> None:
        self.closed += 1


@pytest.mark.asyncio
async def test_curl_websocket_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    socket = Socket()
    session = Session(socket)
    monkeypatch.setattr(
        "tvfinance.core.websocket.requests.AsyncSession", lambda **_: session
    )
    adapter = await CurlWebSocket.open("wss://example", headers={})
    await adapter.send_text("message")
    assert await adapter.receive_text(timeout=1) == "hello"
    await adapter.close()
    await adapter.close()
    assert socket.closed == session.closed == 1


@pytest.mark.asyncio
async def test_curl_websocket_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    failure = RequestException("failed")
    session = Session(failure)
    monkeypatch.setattr(
        "tvfinance.core.websocket.requests.AsyncSession", lambda **_: session
    )
    with pytest.raises(TransportError):
        await CurlWebSocket.open("wss://example", headers={})
    assert session.closed == 1

    socket = Socket()
    adapter = CurlWebSocket(Session(socket), socket)
    socket.value = failure
    with pytest.raises(TransportError):
        await adapter.send_text("x")
    with pytest.raises(TransportError):
        await adapter.receive_text(timeout=1)
    socket.value = TimeoutError()
    with pytest.raises(RequestTimeoutError):
        await adapter.receive_text(timeout=1)


def test_decode_methods() -> None:
    messages, suffix = decode_methods(
        encode_frame("~h~1") + encode_frame("[]") + encode_frame('{"m":"ok"}')
    )
    assert messages == [{"m": "ok"}]
    assert suffix == ""
    with pytest.raises(ProtocolError):
        decode_methods(encode_frame("invalid"))
