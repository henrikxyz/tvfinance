from __future__ import annotations

import pytest

from tvfinance.core import (
    CachedTransport,
    HttpRequest,
    HttpResponse,
    MemoryResponseCache,
    ValidationError,
    request_cache_key,
)


class FakeTransport:
    def __init__(self, responses: list[HttpResponse]) -> None:
        self.responses = responses
        self.requests: list[HttpRequest] = []
        self.closed = False

    async def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.responses.pop(0)

    async def close(self) -> None:
        self.closed = True


def test_cache_key_includes_headers_and_normalizes_method() -> None:
    first = HttpRequest("get", "https://example.test", headers={"Language": "en"})
    same = HttpRequest("GET", "https://example.test", headers={"language": "en"})
    different = HttpRequest("GET", "https://example.test", headers={"language": "ja"})
    assert request_cache_key(first) == request_cache_key(same)
    assert request_cache_key(first) != request_cache_key(different)


def test_memory_cache_expiration_and_clear() -> None:
    now = [10.0]
    cache = MemoryResponseCache(ttl=5, clock=lambda: now[0])
    response = HttpResponse(200, b"ok")
    assert cache.get("missing") is None
    cache.set("key", response)
    assert len(cache) == 1
    assert cache.get("key") is response
    now[0] = 15.0
    assert cache.get("key") is None
    cache.set("key", response)
    cache.clear()
    assert len(cache) == 0
    with pytest.raises(ValidationError):
        MemoryResponseCache(ttl=0)


@pytest.mark.asyncio
async def test_cached_transport_only_caches_successful_gets() -> None:
    responses = [
        HttpResponse(200, b"one"),
        HttpResponse(500, b"error"),
        HttpResponse(201, b"created"),
    ]
    inner = FakeTransport(responses)
    transport = CachedTransport(inner, MemoryResponseCache())
    get = HttpRequest("GET", "https://example.test/one")
    failed_get = HttpRequest("GET", "https://example.test/error")
    post = HttpRequest("POST", "https://example.test")

    assert await transport.send(get) == await transport.send(get)
    await transport.send(failed_get)
    await transport.send(post)
    assert len(inner.requests) == 3
    await transport.close()
    assert inner.closed is True
