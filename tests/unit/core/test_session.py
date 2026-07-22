from __future__ import annotations

import pytest

from tvfinance.core import AsyncClientSession, HttpRequest, HttpResponse


class FakeTransport:
    def __init__(self) -> None:
        self.closed = 0

    async def send(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse(200, request.url.encode())

    async def close(self) -> None:
        self.closed += 1


@pytest.mark.asyncio
async def test_async_client_session_context_and_request() -> None:
    transport = FakeTransport()
    async with AsyncClientSession(transport=transport) as session:
        response = await session.request(HttpRequest("GET", "https://example.test"))
        assert response.text == "https://example.test"
    await session.close()
    assert transport.closed == 1


def test_async_client_session_builds_default_stack() -> None:
    session = AsyncClientSession()
    assert session.settings.timeout == 30.0


def test_async_client_session_builds_cached_stack() -> None:
    from tvfinance.core import MemoryResponseCache

    session = AsyncClientSession(cache=MemoryResponseCache())
    assert session.settings.retry.attempts == 3
