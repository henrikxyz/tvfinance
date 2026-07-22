"""Response caching with deterministic, request-complete keys."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from tvfinance.core.contracts import HttpRequest, HttpResponse
from tvfinance.core.types import JsonValue
from tvfinance.core.validation import positive_number

SCHEMA_VERSION = 1


class ResponseCache(Protocol):
    """Storage contract used by cached transports."""

    def get(self, key: str) -> HttpResponse | None:
        """Return one fresh cached response."""
        ...

    def set(self, key: str, response: HttpResponse) -> None:
        """Store one response."""
        ...

    def clear(self) -> None:
        """Remove all cached responses."""
        ...


def request_cache_key(request: HttpRequest) -> str:
    """Hash every request field that can influence a response."""
    canonical: dict[str, JsonValue] = {
        "method": request.method.upper(),
        "url": request.url,
        "headers": {key.lower(): value for key, value in request.headers.items()},
        "params": cast(JsonValue, request.params),
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


class SQLiteResponseCache:
    """Persistent TTL and LRU response cache safe for multiple processes."""

    def __init__(
        self,
        path: str | Path,
        *,
        ttl: float = 3600,
        max_entries: int = 10_000,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.path = Path(path)
        self.ttl = positive_number(ttl, field="ttl")
        if max_entries < 1:
            positive_number(float(max_entries), field="max_entries")
        self.max_entries = max_entries
        self._clock = clock
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS cache_meta "
                "(key TEXT PRIMARY KEY, value INTEGER NOT NULL)"
            )
            version = connection.execute(
                "SELECT value FROM cache_meta WHERE key = 'schema_version'"
            ).fetchone()
            if version is not None and int(version[0]) != SCHEMA_VERSION:
                connection.execute("DROP TABLE IF EXISTS response_cache")
                connection.execute("DELETE FROM cache_meta")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS response_cache ("
                "key TEXT PRIMARY KEY, status_code INTEGER NOT NULL, "
                "body BLOB NOT NULL, headers TEXT NOT NULL, "
                "expires_at REAL NOT NULL, accessed_at REAL NOT NULL)"
            )
            connection.execute(
                "INSERT OR REPLACE INTO cache_meta(key, value) VALUES "
                "('schema_version', ?)",
                (SCHEMA_VERSION,),
            )

    def get(self, key: str) -> HttpResponse | None:
        now = self._clock()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status_code, body, headers, expires_at "
                "FROM response_cache WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            if float(row[3]) <= now:
                connection.execute("DELETE FROM response_cache WHERE key = ?", (key,))
                return None
            connection.execute(
                "UPDATE response_cache SET accessed_at = ? WHERE key = ?",
                (now, key),
            )
        headers = json.loads(str(row[2]))
        return HttpResponse(
            int(row[0]),
            bytes(row[1]),
            {str(name): str(value) for name, value in headers.items()},
        )

    def set(self, key: str, response: HttpResponse) -> None:
        now = self._clock()
        headers = json.dumps(response.headers, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO response_cache "
                "(key, status_code, body, headers, expires_at, accessed_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    key,
                    response.status_code,
                    response.body,
                    headers,
                    now + self.ttl,
                    now,
                ),
            )
            connection.execute(
                "DELETE FROM response_cache WHERE expires_at <= ?", (now,)
            )
            excess = (
                int(
                    connection.execute(
                        "SELECT COUNT(*) FROM response_cache"
                    ).fetchone()[0]
                )
                - self.max_entries
            )
            if excess > 0:
                connection.execute(
                    "DELETE FROM response_cache WHERE key IN "
                    "(SELECT key FROM response_cache "
                    "ORDER BY accessed_at ASC, key ASC LIMIT ?)",
                    (excess,),
                )

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM response_cache")

    def __len__(self) -> int:
        with self._connect() as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM response_cache").fetchone()[0]
            )
