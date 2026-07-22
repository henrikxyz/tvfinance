# TVFinance

TVFinance helps Python users look up market quotes, price history, news,
options, calendars, and company information. Use it from synchronous or async
Python, a JSON command line, or the optional MCP server.

## Start here

The [getting-started tutorial](getting-started.md) covers environment setup,
symbol discovery, a quote, historical bars, and serialization. Continue with a
task guide when the first script works:

- [Python API](guide/python.md): clients, async, tickers, options, research, and
  errors.
- [Command line](guide/cli.md): every command and JSON pipelines.
- [MCP server](guide/mcp.md): installation, client configuration, tool list,
  and data-use cautions.
- [Caching](guide/cache.md): in-memory and persistent SQLite behavior.
- [Troubleshooting](guide/troubleshooting.md): common input, event-loop,
  transport, rate-limit, cache, and MCP failures.

!!! danger "Unofficial TradingView integration"

    Public reachability does not grant permission to access or use provider
    data. TradingView's terms restrict non-display, automated, algorithmic,
    commercial, and redistribution uses. Review the
    [provider policy notice](https://github.com/henrikxyz/TVFinance/blob/main/TRADINGVIEW_POLICY.md)
    and official terms before using this package. The data must not be treated
    as financial advice.

!!! warning "AI-generated project"

    This project was substantially generated with help from large language
    models. Code and documentation can be incorrect and require independent
    human review. Read the
    [AI disclosure](https://github.com/henrikxyz/TVFinance/blob/main/AI_DISCLOSURE.md).

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

Results are immutable typed models. Call `to_dict()` when ordinary JSON-safe
data is needed. Quote fields may be `None`, and market data may be delayed,
incomplete, or incorrect.
