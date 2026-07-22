# Caching

Caching reduces repeated provider requests and can make short-lived scripts
more predictable. TVFinance provides an in-memory cache and a persistent SQLite
cache without adding another dependency.

!!! warning "A cache is stored provider data"

    Confirm that storage is permitted for your use case. Choose an appropriate
    TTL, protect the cache file like other application data, and do not publish
    it. Clearing a cache does not revoke copies made elsewhere.

## In-memory cache

Use `MemoryResponseCache` when results only need to live for the current Python
process:

```python
from tvfinance import Client
from tvfinance.core import MemoryResponseCache

cache = MemoryResponseCache(ttl=300)
client = Client(cache=cache)

first = client.quote("NASDAQ:AAPL")
second = client.quote("NASDAQ:AAPL")

print("cached entries:", len(cache))
cache.clear()
```

`ttl` is measured in seconds and must be positive. The cache is not shared with
another process and disappears when the process exits.

## Persistent SQLite cache

Use `SQLiteResponseCache` when a later process should reuse a fresh response:

~~~python
from tvfinance import Client
from tvfinance.core import SQLiteResponseCache

cache = SQLiteResponseCache(
    ".cache/tvfinance.sqlite3",
    ttl=900,
    max_entries=10_000,
)
client = Client(cache=cache)
quote = client.quote("NASDAQ:AAPL")
~~~

Parent directories are created automatically. `max_entries` bounds growth;
expired entries are removed and the least recently used entries are evicted
when the capacity is exceeded.

Close all application operations before deleting the database. Clear records
through the API when the file should remain in place:

```python
print("stored entries:", len(cache))
cache.clear()
```

## What forms the cache key

The key hashes every request field that can affect a response: method, URL,
normalized headers, query parameters, and JSON body. This prevents two
different requests from accidentally sharing one response.

SQLite stores response bodies and response headers. Request headers,
credentials, and cookies are not stored as separate readable columns, but the
request-complete hash can still reflect request differences. The database uses
transactions, WAL mode, schema versioning, and a five-second busy timeout for
multi-process access.

## Choosing a TTL

There is no universally safe TTL. Quotes may need seconds or minutes; profiles
may tolerate hours. A longer TTL lowers request volume but increases the chance
of reading stale data. The cache never promises market freshness—always inspect
the provider timestamp on time-sensitive results.
