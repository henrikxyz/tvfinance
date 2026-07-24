# TVFinance

[![PyPI](https://img.shields.io/pypi/v/tvfinance?logo=pypi&logoColor=white)](https://pypi.org/project/tvfinance/)
[![Python](https://img.shields.io/pypi/pyversions/tvfinance?logo=python&logoColor=white)](https://pypi.org/project/tvfinance/)
[![CI](https://img.shields.io/github/actions/workflow/status/henrikxyz/tvfinance/ci.yml?branch=main&logo=github&label=CI)](https://github.com/henrikxyz/tvfinance/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/github/actions/workflow/status/henrikxyz/TVFinance/docs.yml?branch=main&logo=materialformkdocs&logoColor=white&label=docs)](https://henrikxyz.github.io/TVFinance/)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](https://github.com/henrikxyz/tvfinance/actions/workflows/ci.yml)
[![License](https://img.shields.io/pypi/l/tvfinance)](LICENSE)

> [!CAUTION]
> **STOP: TradingView legal and data-use restrictions.** TVFinance is an
> independent, unofficial project. It is not affiliated with,
> sponsored by, endorsed by, or vetted by TradingView. TradingView's terms
> describe market data as display-only and restrict non-display, automated,
> algorithmic, commercial, and redistribution uses, including third-party tools
> that enable restricted uses. TVFinance does not grant permission or a data
> license. Before using it, read the [TradingView policy notice](TRADINGVIEW_POLICY.md),
> the [official TradingView terms](https://www.tradingview.com/policies/), and
> the full [disclaimer](DISCLAIMER.md).

> [!WARNING]
> This project was substantially generated with help from large language
> models. Its code, tests, documentation, and output may contain mistakes and
> require independent human review. Market data may be delayed, incomplete, or
> incorrect. Do not use this software as financial or investment advice. Read
> the [AI disclosure](AI_DISCLOSURE.md) before using or contributing.

TVFinance is a Python library for looking up market information. You can search
for symbols, check current quotes, download price history, read company news,
and explore financial data without assembling several different tools.

It works in regular and async Python programs, from the command line, and as an
optional MCP server for AI applications. Python 3.10 through 3.14 are supported.
The complete [documentation](https://henrikxyz.github.io/TVFinance/) includes
the Python, CLI, MCP, cache, API, architecture, and development guides.

## Features

- Find stocks, ETFs, bonds, indexes, futures, currencies, and cryptocurrencies.
- Check one quote or follow live price updates.
- Download historical prices at different time intervals.
- Filter markets with screeners and explore option chains.
- Read company profiles, financials, forecasts, filings, and news.
- View earnings, dividend, revenue, IPO, and economic calendars.
- Use a simple Python API, async API, command-line tool, or optional MCP server.
- Cache results in memory or in a local SQLite file.

## Installation

~~~bash
pip install tvfinance
pip install "tvfinance[mcp]"
~~~

Install the MCP extra only when you need to connect TVFinance to an MCP client.

## Quick start

~~~python
import tvfinance

quote = tvfinance.quote("NASDAQ:AAPL")
bars = tvfinance.history("NASDAQ:AAPL", resolution="1D", count=30)
profile = tvfinance.profile("NASDAQ:AAPL")
~~~

For async applications, use `tvfinance.aio`:

~~~python
from tvfinance import aio

quote = await aio.quote("NASDAQ:AAPL")
bars = await aio.history("NASDAQ:AAPL", count=30)
~~~

For several requests, reuse one client connection:

~~~python
from tvfinance import AsyncClient

async with AsyncClient() as client:
    quote = await client.quote("NASDAQ:AAPL")
    news = await client.news("NASDAQ:AAPL", fetch_body=True)
~~~

Command-line and MCP entry points:

~~~bash
tvfinance --help
tvfinance history NASDAQ:AAPL --count 30
tvfinance-mcp
~~~

The optional MCP server supports local stdio clients and Streamable HTTP. It
exposes the complete high-level async client surface with AI-readable tool
schemas and safety instructions. See the
[MCP guide](https://henrikxyz.github.io/TVFinance/guide/mcp/) for configuration,
all 16 tools, Prefect Horizon hosting, and network-exposure precautions.

## Development

```bash
uv sync --group dev
uv run ruff format .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv build
```

## Important information

Version 26.0.1 is the current stable release of the rebuilt package. Provider
endpoints are unofficial and may change. This project is for research and does
not provide financial advice.

## Legal and provider notice

TradingView and related names and marks belong to their respective owners.
TVFinance is not affiliated with, endorsed by, or vetted by TradingView. The
software uses unofficial interfaces and provides no rights to provider content
or market data.

Do not assume that research, educational, personal, internal, AI, or MCP use is
automatically permitted. You must determine whether your exact access, display,
storage, processing, and redistribution are authorized. If you need automated
trading, algorithmic processing, commercial use, redistribution, or another
non-display use, obtain explicit permission and a suitable licensed data feed.
See [TRADINGVIEW_POLICY.md](TRADINGVIEW_POLICY.md) for the provider-policy
summary and links to the controlling terms.
