"""Unified asynchronous client session composition."""

from __future__ import annotations

from tvfinance.core.cache import MemoryResponseCache
from tvfinance.core.contracts import AsyncHttpTransport, HttpRequest, HttpResponse
from tvfinance.core.settings import ClientSettings
from tvfinance.core.transport import CachedTransport, CurlHttpTransport, RetryTransport


class AsyncClientSession:
    """Own or wrap the transport stack used by domain services."""

    def __init__(
        self,
        *,
        settings: ClientSettings | None = None,
        transport: AsyncHttpTransport | None = None,
        cache: MemoryResponseCache | None = None,
    ) -> None:
        self.settings = settings or ClientSettings()
        if transport is None:
            composed: AsyncHttpTransport = RetryTransport(
                CurlHttpTransport(), self.settings.retry
            )
            if cache is not None:
                composed = CachedTransport(composed, cache)
            self._transport = composed
        else:
            self._transport = transport
        self._closed = False

    async def request(self, request: HttpRequest) -> HttpResponse:
        return await self._transport.send(request)

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._transport.close()

    async def __aenter__(self) -> AsyncClientSession:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        await self.close()
