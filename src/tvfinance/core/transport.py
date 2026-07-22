"""HTTP transport adapters, retry policies, and cache composition."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol, cast

from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException

from tvfinance.core.cache import ResponseCache, request_cache_key
from tvfinance.core.contracts import AsyncHttpTransport, HttpRequest, HttpResponse
from tvfinance.core.exceptions import RateLimitError, TransportError
from tvfinance.core.settings import RetryPolicy


class _CurlResponse(Protocol):
    status_code: int
    content: bytes
    headers: Mapping[str, str]


class _CurlSession(Protocol):
    async def request(self, method: str, url: str, **kwargs: Any) -> _CurlResponse: ...

    async def close(self) -> None: ...


class CurlHttpTransport:
    """Buffered async HTTP transport implemented with curl-cffi."""

    def __init__(self, session: _CurlSession | None = None) -> None:
        self._session: _CurlSession = (
            session
            if session is not None
            else cast(_CurlSession, requests.AsyncSession(impersonate="chrome"))
        )
        self._closed = False

    async def send(self, request: HttpRequest) -> HttpResponse:
        if self._closed:
            raise TransportError("Transport is closed")
        try:
            response = await self._session.request(
                request.method,
                request.url,
                headers=request.headers,
                params=request.params,
                json=request.json_body,
                timeout=request.timeout,
                allow_redirects=True,
            )
        except RequestException as exc:
            raise TransportError(
                "HTTP request failed",
                retryable=True,
                context={"method": request.method, "url": request.url},
            ) from exc
        return HttpResponse(
            response.status_code,
            response.content,
            {str(key): str(value) for key, value in response.headers.items()},
        )

    async def close(self) -> None:
        if not self._closed:
            self._closed = True
            await self._session.close()


class RetryTransport:
    """Retry transient transport failures and configured response statuses."""

    def __init__(
        self,
        inner: AsyncHttpTransport,
        policy: RetryPolicy,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._inner = inner
        self._policy = policy
        self._sleep = sleep

    async def send(self, request: HttpRequest) -> HttpResponse:
        for attempt in range(self._policy.attempts):
            try:
                response = await self._inner.send(request)
            except TransportError as exc:
                if not exc.retryable or attempt == self._policy.attempts - 1:
                    raise
            else:
                if response.status_code not in self._policy.retry_statuses:
                    return response
                if attempt == self._policy.attempts - 1:
                    self._raise_status(response)
            await self._sleep(self._delay(attempt))
        raise AssertionError("Retry loop exited unexpectedly")  # pragma: no cover

    def _delay(self, attempt: int) -> float:
        delay = self._policy.base_delay * pow(2.0, attempt)
        return min(
            delay,
            self._policy.maximum_delay,
        )

    @staticmethod
    def _raise_status(response: HttpResponse) -> None:
        if response.status_code == 429:
            retry_after = _retry_after(response.headers.get("retry-after"))
            raise RateLimitError(retry_after=retry_after)
        raise TransportError(
            "Provider returned a transient server error",
            retryable=True,
            status_code=response.status_code,
        )

    async def close(self) -> None:
        await self._inner.close()


def _retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return max(0.0, parsed)


class CachedTransport:
    """Cache successful GET responses around another transport."""

    def __init__(self, inner: AsyncHttpTransport, cache: ResponseCache) -> None:
        self._inner = inner
        self._cache = cache

    async def send(self, request: HttpRequest) -> HttpResponse:
        key = request_cache_key(request) if request.method.upper() == "GET" else None
        cached = self._cache.get(key) if key is not None else None
        if cached is not None:
            return cached
        response = await self._inner.send(request)
        if key is not None and 200 <= response.status_code < 300:
            self._cache.set(key, response)
        return response

    async def close(self) -> None:
        await self._inner.close()
