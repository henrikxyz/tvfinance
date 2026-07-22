# Command line

The base package installs a `tvfinance` command. Results are formatted as
UTF-8 JSON, so the same command can be inspected by a person or passed to a
JSON-aware tool.

## Install and inspect

```bash
python -m pip install tvfinance
tvfinance --version
tvfinance --help
```

Run `tvfinance <command> --help` to inspect the flags for one operation.

## Find and quote a symbol

```bash
tvfinance search Apple
tvfinance quote NASDAQ:AAPL
```

Search first if the fully qualified provider symbol is unknown. Quote output
contains the symbol, current fields, currency, and provider timestamp. A field
can be `null` when the exchange does not supply it.

## History, options, and market discovery

```bash
tvfinance history NASDAQ:AAPL --resolution 1D --count 100
tvfinance history NASDAQ:AAPL --resolution 1D --count max
tvfinance screener --market america --limit 20
tvfinance option-series NASDAQ:AAPL
tvfinance options NASDAQ:AAPL
```

For a reproducible option chain, read `root` and `expiration` from
`option-series`, then pass both:

```bash
tvfinance options NASDAQ:AAPL --root AAPL --expiration 1784851200
```

The expiration is the provider's Unix timestamp, not a formatted date.

## News, research, and calendars

```bash
tvfinance news NASDAQ:AAPL --limit 5
tvfinance news NASDAQ:AAPL --limit 5 --body
tvfinance news-markdown NASDAQ:AAPL --limit 5
tvfinance research NASDAQ:AAPL profile
tvfinance research NASDAQ:AAPL financials
tvfinance calendar earnings --from-date 2026-07-01 --to-date 2026-07-31 --limit 25
```

`news --body` fetches article bodies in addition to metadata and therefore does
more work than the default command. `news-markdown` produces a JSON string whose
value contains the combined Markdown documents.

Research sections are `bonds`, `etfs`, `documents`, `holdings`, `ideas`,
`financials`, `forecast`, `technicals`, and `profile`. Availability varies by
asset type.

## Use JSON in a pipeline

=== "PowerShell"

    ```powershell
    $quote = tvfinance quote NASDAQ:AAPL | ConvertFrom-Json
    $quote.last
    ```

=== "jq"

    ```bash
    tvfinance quote NASDAQ:AAPL | jq '.last'
    tvfinance history NASDAQ:AAPL --count 5 | jq 'map(.close)'
    ```

Version and help output are plain text. Successful data commands write JSON to
standard output. Invalid arguments are rejected before a network request; a
provider or validation failure exits non-zero.

## Command summary

| Command | Purpose |
| --- | --- |
| `search QUERY` | Discover qualified symbols |
| `quote SYMBOL` | Retrieve one quote snapshot |
| `screener` | Query one provider market screener |
| `history SYMBOL` | Retrieve OHLCV bars |
| `option-series SYMBOL` | List option roots and expirations |
| `options SYMBOL` | Retrieve a paired call/put chain |
| `news SYMBOL` | Retrieve news metadata and optional bodies |
| `news-markdown SYMBOL` | Render fetched articles as Markdown |
| `research SYMBOL SECTION` | Retrieve a company or asset research section |
| `calendar CATEGORY` | Retrieve earnings, revenue, dividend, or IPO events |
