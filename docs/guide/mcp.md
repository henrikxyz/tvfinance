# MCP server

MCP is optional and uses the shared async API rather than a separate
implementation.

!!! danger "Provider data rights"

    MCP is a technical interface, not permission to send provider data to an AI
    system or use it for machine-driven processing. TradingView's terms include
    restrictions on non-display use and third-party tools that enable restricted
    uses. Do not use TradingView-derived data through MCP unless you have
    independently established all necessary access and data rights. Read the
    [provider policy notice](https://github.com/henrikxyz/tvfinance/blob/main/TRADINGVIEW_POLICY.md).

~~~bash
pip install "tvfinance[mcp]"
tvfinance-mcp
~~~

The module entry point is equivalent:

~~~bash
python -m tvfinance.mcp
~~~

## Configure an MCP client

Configure the client to launch the installed executable over its standard MCP
transport. The exact settings screen differs between clients, but the command
and arguments are equivalent to:

```json
{
  "command": "tvfinance-mcp",
  "args": []
}
```

If the executable is not on the client's `PATH`, use the absolute path inside
the virtual environment. For example, it is commonly
`.venv\\Scripts\\tvfinance-mcp.exe` on Windows and
`.venv/bin/tvfinance-mcp` on macOS or Linux.

Restart or reload the MCP client after changing its server configuration. A
successful connection exposes a server named `tvfinance`.

## Available tools

| Tool | Important inputs | Result |
| --- | --- | --- |
| `search_symbols` | `query` | Matching symbols |
| `get_quote` | `symbol` | One quote snapshot |
| `get_quotes` | `symbols` | Several quote snapshots |
| `get_quote_updates` | `symbols`, `updates` | A bounded sample of live updates |
| `query_screener` | `market`, `limit` | Screener rows |
| `get_history` | `symbol`, `resolution`, `count` | OHLCV bars |
| `get_option_series` | `symbol` | Option roots and expirations |
| `get_options_chain` | `symbol`, optional `root` and `expiration` | Paired call/put rows |
| `get_news` | `symbol`, `limit` | News metadata |
| `get_news_markdown` | `symbol`, `limit` | Article Markdown |
| `get_research` | `symbol`, `section` | One research section |
| `get_corporate_calendar` | category, date range, limit | Corporate events |
| `get_economic_calendar` | date range, countries | Economic events |

Symbols use `EXCHANGE:NAME`. Date inputs use ISO 8601 strings. Option
expirations use provider Unix timestamps.

## Safer prompting and tool use

Do not instruct an AI client to perform unbounded polling or bulk collection.
Set small `limit`, `count`, and `updates` values, request only the instruments
needed for the current task, and review tool output before relying on it. MCP
does not turn provider data into verified facts or investment advice.

## Verify or troubleshoot startup

```bash
python -c "from tvfinance.mcp import create_server; print(create_server().name)"
```

If Python reports that optional dependencies are missing, the base package was
installed without its extra. Install `tvfinance[mcp]` into the exact Python
environment used by the MCP client. If a client cannot find the executable,
use its absolute path rather than installing a second global copy.

Importing `tvfinance` alone does not import FastMCP. The optional dependency is
loaded only when the MCP server is created.
