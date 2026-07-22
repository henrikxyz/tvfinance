# Getting started

This guide takes you from a clean Python environment to a quote and a short
price history. It also explains the values returned by TVFinance so that the
first example is useful rather than just executable.

!!! danger "Check provider rights first"

    TVFinance is an unofficial integration. Technical access does not grant a
    licence to retrieve, process, store, or redistribute provider data. Read
    the [provider policy notice](https://github.com/henrikxyz/TVFinance/blob/main/TRADINGVIEW_POLICY.md)
    before use. Nothing returned by this package is financial advice.

## 1. Create an environment

TVFinance supports Python 3.10 through 3.14. A virtual environment keeps it
separate from the rest of your Python installation.

=== "Windows PowerShell"

    ```powershell
    py -3.14 -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install tvfinance
    ```

=== "macOS and Linux"

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install tvfinance
    ```

Confirm that the command-line entry point is available:

```bash
tvfinance --version
```

Install `tvfinance[mcp]` instead of the base package only when an MCP client
needs to launch the optional server.

## 2. Find the provider symbol

Market operations use a fully qualified `EXCHANGE:NAME` symbol. Search first
when the exchange or provider spelling is uncertain:

```python
import tvfinance

for result in tvfinance.search("Apple")[:5]:
    print(result.symbol.ticker, result.description, result.asset_type)
```

Search results contain a typed `Symbol`, description, asset type, currency, and
provider identifier when available. For Apple on Nasdaq, later examples use
`NASDAQ:AAPL`.

## 3. Request a quote

Create `quickstart.py`:

```python
import tvfinance

quote = tvfinance.quote("NASDAQ:AAPL")

print("symbol:", quote.symbol.ticker)
print("last:", quote.last)
print("change %:", quote.change_percent)
print("currency:", quote.currency)
print("provider time:", quote.timestamp)
```

Run it with `python quickstart.py`. Quote fields are optional because exchanges
and asset classes do not all publish the same fields. Check for `None` instead
of assuming every value exists.

## 4. Request price history

```python
bars = tvfinance.history(
    "NASDAQ:AAPL",
    resolution="1D",
    count=30,
)

for bar in bars[-5:]:
    print(bar.timestamp.date(), bar.open, bar.high, bar.low, bar.close, bar.volume)
```

Each item is an immutable `Candle` with a timezone-aware timestamp and OHLCV
fields. `resolution="1D"` requests daily bars; `count=30` limits the requested
series. Availability still depends on the provider and instrument.

## 5. Convert results to JSON-safe data

All public result models provide `to_dict()`. Datetimes become ISO 8601 strings
and nested models become ordinary dictionaries and lists:

```python
import json

print(json.dumps(quote.to_dict(), ensure_ascii=False, indent=2))
```

## Choose the next guide

- Use the [Python API](guide/python.md) for async code, reusable clients,
  options, news, research, calendars, and error handling.
- Use the [command line](guide/cli.md) for scripts and JSON pipelines.
- Use the [MCP server](guide/mcp.md) only after reviewing the additional
  provider-data implications.
- Add the [persistent cache](guide/cache.md) when repeated requests need to
  survive process restarts.
- Start with [troubleshooting](guide/troubleshooting.md) when a symbol, network
  call, event loop, or optional dependency fails.
