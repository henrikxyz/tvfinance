# Persistent cache

The default cache is process-local. SQLiteResponseCache provides an optional
persistent backend without adding dependencies.

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

The cache uses hashed request-complete keys, TTL expiration, least-recently-used
capacity cleanup, schema versioning, SQLite transactions, WAL mode, and a busy
timeout for multi-process access. Response bodies and response headers are
stored; request headers and credentials are not persisted.
