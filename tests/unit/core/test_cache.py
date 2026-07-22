from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from tvfinance.core import (
    CachedTransport,
    HttpRequest,
    HttpResponse,
    MemoryResponseCache,
    SQLiteResponseCache,
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


def test_sqlite_cache_persists_expires_and_clears(tmp_path: Path) -> None:
    now = [10.0]
    path = tmp_path / "nested" / "cache.sqlite3"
    response = HttpResponse(200, b"payload", {"content-type": "text/plain"})
    cache = SQLiteResponseCache(path, ttl=5, max_entries=2, clock=lambda: now[0])
    assert cache.get("missing") is None
    cache.set("one", response)
    assert len(cache) == 1

    reopened = SQLiteResponseCache(path, ttl=5, max_entries=2, clock=lambda: now[0])
    assert reopened.get("one") == response
    now[0] = 15.0
    assert reopened.get("one") is None
    assert len(reopened) == 0
    reopened.set("two", response)
    reopened.clear()
    assert len(reopened) == 0


def test_sqlite_cache_lru_and_schema_migration(tmp_path: Path) -> None:
    now = [1.0]
    path = tmp_path / "cache.sqlite3"
    cache = SQLiteResponseCache(path, ttl=100, max_entries=2, clock=lambda: now[0])
    response = HttpResponse(200, b"ok")
    cache.set("one", response)
    now[0] = 2.0
    cache.set("two", response)
    now[0] = 3.0
    assert cache.get("one") == response
    now[0] = 4.0
    cache.set("three", response)
    assert cache.get("two") is None
    assert cache.get("one") == response
    assert cache.get("three") == response

    with sqlite3.connect(path) as connection:
        connection.execute(
            "UPDATE cache_meta SET value = 999 WHERE key = 'schema_version'"
        )
    migrated = SQLiteResponseCache(path)
    assert len(migrated) == 0


@pytest.mark.parametrize(
    "kwargs",
    [{"ttl": 0}, {"max_entries": 0}],
)
def test_sqlite_cache_validates_configuration(
    tmp_path: Path, kwargs: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        SQLiteResponseCache(tmp_path / "cache.sqlite3", **kwargs)
