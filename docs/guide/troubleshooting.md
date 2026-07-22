# Troubleshooting

Start with the exception message and type. TVFinance separates input,
configuration, transport, timeout, rate-limit, protocol, and parsing failures
so an application does not need to treat every failure as "no data".

## A symbol is rejected or returns no result

Symbols must use `EXCHANGE:NAME`, for example `NASDAQ:AAPL`. Run
`tvfinance search Apple` or `tvfinance.search("Apple")` and use the returned
`result.symbol.ticker`. Do not assume that a familiar display ticker identifies
one unique exchange or instrument.

If a valid symbol returns no quote, the provider may not expose that field or
instrument to the current anonymous session. Do not replace `None` with zero.

## Synchronous API cannot run inside an event loop

This commonly occurs in async web frameworks and notebooks. Replace:

```python
quote = tvfinance.quote("NASDAQ:AAPL")
```

with:

```python
from tvfinance import aio

quote = await aio.quote("NASDAQ:AAPL")
```

For repeated work, use `async with AsyncClient() as client`.

## Timeout, network, or rate-limit errors

- Confirm ordinary HTTPS access works from the same machine and environment.
- Avoid tight polling loops and reduce batch size.
- Respect `retry_after` when a `RateLimitError` provides it.
- Set a deliberate timeout and retry policy instead of retrying forever.
- Treat a repeated provider rejection as a stop condition, not an invitation to
  evade access controls.

```python
from tvfinance import Client
from tvfinance.core import ClientSettings, RetryPolicy

client = Client(
    settings=ClientSettings(
        timeout=15,
        retry=RetryPolicy(attempts=2, base_delay=1, maximum_delay=4),
    )
)
```

## MCP optional dependency is missing

Install the extra into the environment used by the MCP client:

```bash
python -m pip install "tvfinance[mcp]"
python -m tvfinance.mcp
```

If the terminal succeeds but the MCP client fails, the client is probably
using another Python environment or cannot find the executable. Configure the
absolute virtual-environment path.

## Cached data looks stale

Inspect the result timestamp, shorten the cache TTL, or call `cache.clear()`.
Deleting only the main SQLite file while another process is active can leave
WAL-related files or cause errors; stop users of the cache first.

## Provider response changed

A `ProtocolError` or `ParseError` can indicate an upstream format change.
Confirm the installed TVFinance version, check repository issues, and keep the
original exception type and non-sensitive context. Do not attach cookies,
authorization headers, full private responses, or account identifiers to a bug
report.

## Report a reproducible problem

Include:

1. TVFinance and Python versions.
2. Operating system and sync, async, CLI, or MCP interface.
3. A minimal example using a public symbol.
4. Exception type, message, and sanitized context.
5. Whether the problem reproduces with the cache disabled.

Use the [GitHub issue tracker](https://github.com/henrikxyz/TVFinance/issues).
Review the [AI disclosure](https://github.com/henrikxyz/TVFinance/blob/main/AI_DISCLOSURE.md)
before relying on generated code or documentation.
