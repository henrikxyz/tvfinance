"""Injectable transport contracts used by domain services."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol, cast

from tvfinance.core.types import Headers, JsonValue, QueryParams


@dataclass(frozen=True, slots=True)
class HttpRequest:
    """Provider-neutral HTTP request."""

    method: str
    url: str
    headers: Headers = field(default_factory=dict)
    params: QueryParams = field(default_factory=dict)
    json_body: JsonValue = None
    timeout: float = 30.0


@dataclass(frozen=True, slots=True)
class HttpResponse:
    """Provider-neutral buffered HTTP response."""

    status_code: int
    body: bytes
    headers: Headers = field(default_factory=dict)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")

    def json(self) -> JsonValue:
        return cast(JsonValue, json.loads(self.body))


class AsyncHttpTransport(Protocol):
    """Asynchronous buffered HTTP transport."""

    async def send(self, request: HttpRequest) -> HttpResponse:
        """Send one request and return its buffered response."""
        ...

    async def close(self) -> None:
        """Release owned resources."""
        ...


class AsyncWebSocket(Protocol):
    """Minimal WebSocket interface required by provider adapters."""

    async def send_text(self, message: str) -> None:
        """Send a text frame."""
        ...

    async def receive_text(self, *, timeout: float) -> str:
        """Receive one text frame before the timeout."""
        ...

    async def close(self) -> None:
        """Close the socket."""
        ...
