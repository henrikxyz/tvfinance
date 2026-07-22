from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest
from curl_cffi.requests.exceptions import RequestException

from tvfinance.core import (
    CurlHttpTransport,
    HttpRequest,
    HttpResponse,
    RateLimitError,
    RetryPolicy,
    RetryTransport,
    TransportError,
)


class CurlResponse:
    status_code = 200
    content = b"ok"
    headers: Mapping[str, str] = {"X-Test": "yes"}


class CurlSession:
    def __init__(self, error: bool = False) -> None:
        self.error = error
        self.closed = 0
        self.kwargs: dict[str, Any] = {}

    async def request(self, method: str, url: str, **kwargs: Any) -> CurlResponse:
        self.kwargs = {"method": method, "url": url, **kwargs}
        if self.error:
            raise RequestException("offline")
        return CurlResponse()

    async def close(self) -> None:
        self.closed += 1


@pytest.mark.asyncio
async def test_curl_transport_maps_response_and_closes_once() -> None:
    session = CurlSession()
    transport = CurlHttpTransport(session)
    response = await transport.send(HttpRequest("GET", "https://example.test"))
    assert response == HttpResponse(200, b"ok", {"X-Test": "yes"})
    assert session.kwargs["allow_redirects"] is True
    await transport.close()
    await transport.close()
    assert session.closed == 1
    with pytest.raises(TransportError, match="closed"):
        await transport.send(HttpRequest("GET", "https://example.test"))


@pytest.mark.asyncio
async def test_curl_transport_maps_request_exception() -> None:
    transport = CurlHttpTransport(CurlSession(error=True))
    with pytest.raises(TransportError) as caught:
        await transport.send(HttpRequest("GET", "https://example.test"))
    assert caught.value.retryable is True


class SequenceTransport:
    def __init__(self, items: list[HttpResponse | TransportError]) -> None:
        self.items = items
        self.closed = False

    async def send(self, request: HttpRequest) -> HttpResponse:
        item = self.items.pop(0)
        if isinstance(item, TransportError):
            raise item
        return item

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_retry_transport_retries_status_and_error() -> None:
    inner = SequenceTransport(
        [
            TransportError("offline", retryable=True),
            HttpResponse(503, b"busy"),
            HttpResponse(200, b"ok"),
        ]
    )
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    transport = RetryTransport(
        inner,
        RetryPolicy(attempts=3, base_delay=2, maximum_delay=3),
        sleep=sleep,
    )
    assert await transport.send(
        HttpRequest("GET", "https://example.test")
    ) == HttpResponse(200, b"ok")
    assert delays == [2, 3]
    await transport.close()
    assert inner.closed is True


@pytest.mark.asyncio
async def test_retry_transport_stops_for_nonretryable_error() -> None:
    transport = RetryTransport(
        SequenceTransport([TransportError("bad", retryable=False)]), RetryPolicy()
    )
    with pytest.raises(TransportError, match="bad"):
        await transport.send(HttpRequest("GET", "https://example.test"))


@pytest.mark.asyncio
async def test_retry_transport_raises_final_server_error() -> None:
    transport = RetryTransport(
        SequenceTransport([HttpResponse(500, b"bad")]), RetryPolicy(attempts=1)
    )
    with pytest.raises(TransportError) as caught:
        await transport.send(HttpRequest("GET", "https://example.test"))
    assert caught.value.status_code == 500


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("header", "expected"),
    [("2.5", 2.5), ("-1", 0.0), ("soon", None), (None, None)],
)
async def test_retry_transport_maps_rate_limit(
    header: str | None, expected: float | None
) -> None:
    headers = {} if header is None else {"retry-after": header}
    transport = RetryTransport(
        SequenceTransport([HttpResponse(429, b"slow", headers)]),
        RetryPolicy(attempts=1),
    )
    with pytest.raises(RateLimitError) as caught:
        await transport.send(HttpRequest("GET", "https://example.test"))
    assert caught.value.retry_after == expected


@pytest.mark.asyncio
async def test_retry_transport_raises_last_retryable_error() -> None:
    transport = RetryTransport(
        SequenceTransport([TransportError("offline", retryable=True)]),
        RetryPolicy(attempts=1),
    )
    with pytest.raises(TransportError, match="offline"):
        await transport.send(HttpRequest("GET", "https://example.test"))
