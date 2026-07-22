# Python API

TVFinance offers the same market operations through three styles:

- Functions such as `tvfinance.quote()` are concise for one-off scripts.
- `Client` and `AsyncClient` accept shared settings and cache state.
- `Ticker` and `Tickers` bind repeated operations to one or more symbols.

All market symbols use the `EXCHANGE:NAME` form. Use `search()` rather than
guessing an exchange code.

## Search and quotes

```python
import tvfinance

matches = tvfinance.search("Microsoft")
for match in matches[:5]:
    print(match.symbol.ticker, match.description, match.currency)

quote = tvfinance.quote("NASDAQ:MSFT")
print(quote.last, quote.change_percent, quote.timestamp)
```

Retrieve several snapshots in one provider operation with `quotes()`:

```python
snapshots = tvfinance.quotes(["NASDAQ:MSFT", "NASDAQ:AAPL"])
for symbol, snapshot in snapshots.items():
    if snapshot is None:
        print(symbol, "was not returned")
    else:
        print(symbol, snapshot.last, snapshot.currency)
```

The mapping may contain `None` for an individual symbol. A field inside a
`Quote` can also be `None` when it is unavailable for that asset or exchange.

## Historical bars

```python
bars = tvfinance.history(
    "NASDAQ:MSFT",
    resolution="1D",
    count=100,
    adjustment="splits",
)

closes = [(bar.timestamp, bar.close) for bar in bars]
```

`count` accepts a positive integer or `"max"`. The provider decides which
resolutions and history depth are available. `Candle.timestamp` is
timezone-aware; do not discard its timezone when merging it with other data.

## Reuse configuration and cache state

```python
from tvfinance import Client
from tvfinance.core import ClientSettings, Locale, MemoryResponseCache, RetryPolicy

settings = ClientSettings(
    timeout=15,
    locale=Locale(language="en", region="US"),
    retry=RetryPolicy(attempts=3, base_delay=0.5, maximum_delay=4),
)
cache = MemoryResponseCache(ttl=300)
client = Client(settings=settings, cache=cache)

quote = client.quote("NASDAQ:MSFT")
news = client.news("NASDAQ:MSFT", limit=5)
```

The synchronous `Client` creates a scoped async connection for each operation,
while retaining its settings and cache. Use `AsyncClient` to reuse an actual
network session across multiple calls.

## Async applications

The functional async namespace is convenient for one operation:

```python
from tvfinance import aio

quote = await aio.quote("NASDAQ:MSFT")
```

For a service, notebook, or batch job, keep one client open:

```python
from tvfinance import AsyncClient

async with AsyncClient() as client:
    quote = await client.quote("NASDAQ:MSFT")
    bars = await client.history("NASDAQ:MSFT", count=30)
    news = await client.news("NASDAQ:MSFT", limit=5, fetch_body=True)
```

Never call the synchronous API inside a running event loop. TVFinance rejects
that usage instead of nesting event loops; use `tvfinance.aio` or `AsyncClient`.

Live quote updates are an async iterator and continue until the caller stops:

```python
from tvfinance import aio

received = 0
async for update in aio.stream_quotes(["NASDAQ:MSFT", "NASDAQ:AAPL"]):
    print(update.symbol.ticker, update.last, update.timestamp)
    received += 1
    if received == 10:
        break
```

## Symbol-bound facades

```python
from tvfinance import Ticker, Tickers

msft = Ticker("NASDAQ:MSFT")
print(msft.quote().last)
print(msft.profile().summary)

group = Tickers(["NASDAQ:MSFT", "NASDAQ:AAPL"])
for symbol, snapshot in group.quotes().items():
    print(symbol, snapshot.last if snapshot else None)
```

Use `AsyncTicker` and `AsyncTickers` with `async with` in asynchronous code so
owned sessions are closed deterministically.

## Options

Discover available root/expiration pairs before requesting a deterministic
chain:

```python
series = tvfinance.option_series("NASDAQ:AAPL")
if series:
    selected = series[0]
    chain = tvfinance.options_chain(
        "NASDAQ:AAPL",
        root=selected.root,
        expiration=selected.expiration,
    )
    for row in chain[:10]:
        print(row.strike, row.call, row.put)
```

If `root` or `expiration` is omitted, TVFinance selects the first matching
series. Explicit values make scheduled or reproducible jobs less ambiguous.

## News, research, and calendars

```python
from datetime import datetime, timezone

articles = tvfinance.news("NASDAQ:AAPL", limit=5, fetch_body=False)
profile = tvfinance.profile("NASDAQ:AAPL")
events = tvfinance.earnings(
    from_date=datetime(2026, 7, 1, tzinfo=timezone.utc),
    to_date=datetime(2026, 7, 31, tzinfo=timezone.utc),
    limit=50,
)
```

Research helpers include `profile`, `financials`, `forecast`, `technicals`,
`holdings`, `ideas`, `documents`, `bonds`, and `etfs`. Not every section exists
for every asset class. `ResearchData.records` and `.summary` preserve the
normalized provider values.

## Serialization and errors

Public models are frozen dataclasses and provide JSON-compatible dictionaries:

```python
payload = quote.to_dict()
```

Catch the package base exception when an application needs one error boundary:

```python
from tvfinance import TvFinanceError

try:
    quote = tvfinance.quote("NASDAQ:MSFT")
except TvFinanceError as exc:
    print(exc.message)
    print(dict(exc.context))
```

More specific exceptions distinguish validation, configuration, timeout, rate
limit, transport, protocol, parse, and optional-dependency failures. Diagnostic
context intentionally excludes credentials and response bodies.
