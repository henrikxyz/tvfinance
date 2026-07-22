"""Response caching with deterministic, request-complete keys."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass

from tvfinance.core.contracts import HttpRequest, HttpResponse
from tvfinance.core.types import JsonValue
from tvfinance.core.validation import positive_number


def request_cache_key(request: HttpRequest) -> str:
    """Hash every request field that can influence a response."""
    canonical: dict[str, JsonValue] = {
        "method": request.method.upper(),
        "url": request.url,
        "headers": {key.lower(): value for key, value in request.headers.items()},
        "params": dict(request.params),
        "json": request.json_body,
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    response: HttpResponse
    expires_at: float


class MemoryResponseCache:
    """Process-local TTL cache suitable for clients and deterministic tests."""

    def __init__(
        self,
        *,
        ttl: float = 3600,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.ttl = positive_number(ttl, field="ttl")
        self._clock = clock
        self._entries: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> HttpResponse | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            del self._entries[key]
            return None
        return entry.response

    def set(self, key: str, response: HttpResponse) -> None:
        self._entries[key] = _CacheEntry(response, self._clock() + self.ttl)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
