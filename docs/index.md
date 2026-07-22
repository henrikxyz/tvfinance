# tvfinance

tvfinance provides typed synchronous and asynchronous interfaces for financial
market data research. The same domain services back Python APIs, the command
line, and the optional MCP server.

## Design goals

- Predictable typed results instead of loosely structured dictionaries.
- Async-first internals with explicit synchronous adapters.
- Deterministic offline tests for every parser and protocol operation.
- Optional integrations that do not increase the base installation footprint.
- Clear failures with actionable context and no silently discarded errors.

!!! warning

    Provider endpoints are unofficial and can change without notice. The data is
    for research only and must not be treated as financial advice.

## Install

~~~bash
pip install tvfinance
pip install "tvfinance[mcp]"
~~~

## Minimal example

~~~python
import tvfinance

quote = tvfinance.quote("NASDAQ:AAPL")
history = tvfinance.history("NASDAQ:AAPL", count=30)
~~~
