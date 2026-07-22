# MCP server

TVFinance can expose its public market-data operations to an MCP-compatible AI
client. The MCP extra is optional:

~~~bash
python -m pip install "tvfinance[mcp]"
~~~

!!! danger "Provider data rights"

    MCP is a technical interface, not permission to send provider data to an AI
    system or use it for machine-driven processing. TradingView's terms include
    restrictions on non-display use and third-party tools that enable restricted
    uses. Do not use TradingView-derived data through MCP unless you have
    independently established all necessary access and data rights. Read the
    [provider policy notice](https://github.com/henrikxyz/TVFinance/blob/main/TRADINGVIEW_POLICY.md).

## Choose a transport

### Standard input and output

Use stdio when one desktop AI client launches one local TVFinance process:

~~~bash
tvfinance-mcp
~~~

The module entry point is equivalent:

~~~bash
python -m tvfinance.mcp
~~~

Example MCP client configuration:

~~~json
{
  "mcpServers": {
    "tvfinance": {
      "command": "tvfinance-mcp",
      "args": ["--no-banner"]
    }
  }
}
~~~

If the command is not on `PATH`, use its absolute path. A Windows JSON path must
escape each backslash, for example
`C:\\path\\to\\.venv\\Scripts\\tvfinance-mcp.exe`. On macOS and Linux, a
typical path is `/path/to/.venv/bin/tvfinance-mcp`.

### Streamable HTTP

Use Streamable HTTP when a separately managed local server should accept MCP
connections:

~~~bash
tvfinance-mcp --transport streamable-http
~~~

The default endpoint is `http://127.0.0.1:8000/mcp`. An MCP client that supports
remote URLs can connect to that URL directly.

To select another local port or endpoint path:

~~~bash
tvfinance-mcp --transport streamable-http --port 8765 --path /tvfinance
~~~

The default loopback binding prevents other machines from connecting. Binding
to a non-loopback address requires the explicit `--allow-network` flag:

~~~bash
tvfinance-mcp --transport streamable-http --host 0.0.0.0 --allow-network
~~~

TVFinance does not add authentication or TLS. Do not expose this server directly
to an untrusted network. Put it behind an authenticated TLS reverse proxy and
confirm that your provider rights permit the intended processing before allowing
remote access.

## What an AI client receives

During the MCP handshake, the client receives:

- server instructions covering symbol format, date format, bounded requests,
  the 30-item news limit, provider rights, and financial-risk warnings;
- a title and full description for every tool;
- typed input schemas, including allowed enum values and defaults;
- read-only, non-destructive, idempotent tool annotations.

The website is supporting documentation; an AI client does not need to scrape
this page to discover how the tools work. It learns the operational contract
from the MCP handshake itself.

## Available tools

The MCP surface covers every high-level operation on `tvfinance.AsyncClient`.
It also provides bounded or batch-oriented helpers that are safer for an AI
client. Python-only lifecycle objects, raw transports, and provider internals are
intentionally not MCP tools.

| Tool | Important inputs | Result |
| --- | --- | --- |
| `search_symbols` | `query` | Matching symbols and provider identifiers |
| `get_quote` | `symbol` | One current quote snapshot |
| `get_quotes` | `symbols` | Quote snapshots keyed by symbol |
| `get_quote_updates` | `symbols`, `updates` | A bounded sample of live quote updates |
| `query_screener` | `market`, `columns`, `limit`, `sort_by`, `sort_order` | Ordered screener rows |
| `get_history` | `symbol`, `resolution`, `count`, `adjustment` | OHLCV bars for one symbol |
| `get_histories` | `symbols`, `resolution`, `count`, `adjustment` | OHLCV bars keyed by symbol |
| `get_option_series` | `symbol` | Available option roots and expirations |
| `get_options_chain` | `symbol`, `root`, `expiration` | Paired call and put rows |
| `get_research` | `symbol`, `section` | One normalized research section |
| `get_research_for_symbols` | `symbols`, `section` | One research section keyed by symbol |
| `get_corporate_calendar` | `category`, date range, `limit` | Earnings, revenue, dividend, or IPO events |
| `get_economic_calendar` | date range, `countries`, `importance` | Filtered economic events |
| `get_news` | `symbol`, `limit`, `language`, `fetch_body` | Latest news metadata and optional bodies |
| `get_news_for_symbols` | `symbols`, `limit`, `language`, `fetch_body` | Latest news keyed by symbol |
| `get_news_markdown` | `symbol`, `limit`, `language` | Latest articles rendered as Markdown |

Symbols use `EXCHANGE:NAME`, such as `NASDAQ:AAPL`. Date inputs use ISO 8601.
Option expirations use provider Unix timestamps returned by
`get_option_series`. Research sections are `profile`, `financials`, `forecast`,
`technicals`, `holdings`, `ideas`, `documents`, `bonds`, and `etfs`.

News is a latest-item snapshot, not an archive. The provider returns at most 30
items per symbol and does not expose historical pagination through this feed, so
MCP rejects limits outside `1..30` rather than silently pretending more results
are available.

## Runtime settings

The command exposes the most useful client and cache settings:

~~~text
--timeout SECONDS
--language CODE
--region CODE
--retry-attempts NUMBER
--retry-base-delay SECONDS
--retry-maximum-delay SECONDS
--memory-cache
--cache-path FILE
--cache-ttl SECONDS
--cache-max-entries NUMBER
--no-banner
~~~

`--memory-cache` and `--cache-path` are mutually exclusive. Both stdio and HTTP
reuse one configured asynchronous client for the server lifetime and close it
cleanly on shutdown.

## Verify a connection

First verify that the optional dependency and server can be loaded:

~~~bash
python -c "from tvfinance.mcp import create_server; print(create_server().name)"
~~~

Then connect with the MCP client and confirm that it lists 16 tools. A useful
network-free call is `get_quote_updates` with `updates` set to `0`; it validates
the MCP request and response path without contacting the data provider.

If Python reports missing optional dependencies, install `tvfinance[mcp]` into
the exact Python environment used by the MCP client. If a desktop client cannot
find `tvfinance-mcp`, configure the executable's absolute path and restart that
client.

## Safe use

Keep `limit`, `count`, and `updates` bounded, request only instruments needed for
the current task, and review results before relying on them. Tool results may be
delayed, incomplete, or incorrect. MCP does not turn provider data into verified
facts, permission for automated use, or investment advice.
