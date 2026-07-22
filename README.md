# tvfinance

tvfinance is a typed, async-first Python toolkit for financial market data
research. One domain implementation powers synchronous Python, native async
Python, CLI, and optional MCP interfaces.

Python 3.10 through 3.14 are supported.

## Features

- Symbol search, quote snapshots, batch quotes, live quote updates, and screeners.
- Historical OHLCV bars with configurable resolution and adjustment.
- Option-series discovery and automatically selected option chains.
- Economic, earnings, revenue, dividend, and IPO calendars.
- News metadata, optional article bodies, and Markdown output.
- Company profile, financials, forecasts, technicals, bonds, ETFs, holdings,
  filings, and community ideas.
- Ticker, Tickers, AsyncTicker, and AsyncTickers facades.
- Typed immutable models, strict validation, retry, cache, and structured errors.
- Optional persistent SQLite TTL/LRU cache with no additional dependency.

## Installation

~~~bash
pip install tvfinance
pip install "tvfinance[mcp]"
~~~

No MCP dependency is imported by the base package.

## Quick start

~~~python
import tvfinance

quote = tvfinance.quote("NASDAQ:AAPL")
bars = tvfinance.history("NASDAQ:AAPL", resolution="1D", count=30)
profile = tvfinance.profile("NASDAQ:AAPL")
~~~

Native async calls live in tvfinance.aio:

~~~python
from tvfinance import aio

quote = await aio.quote("NASDAQ:AAPL")
bars = await aio.history("NASDAQ:AAPL", count=30)
~~~

Reuse connections for multiple operations:

~~~python
from tvfinance import AsyncClient

async with AsyncClient() as client:
    quote = await client.quote("NASDAQ:AAPL")
    news = await client.news("NASDAQ:AAPL", fetch_body=True)
~~~

CLI and MCP entry points:

~~~bash
tvfinance --help
tvfinance history NASDAQ:AAPL --count 30
tvfinance-mcp
~~~

## Development

```bash
uv sync --group dev
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

## Status

Version 26.0.0 is the first production release of the rebuilt package. Provider
endpoints are unofficial and may change. This project is for research and does
not provide financial advice.
The project was substantially created with LLM assistance; read the
[AI disclosure](AI_DISCLOSURE.md) before use or contribution.
