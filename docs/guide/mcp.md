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

Available tools cover search, snapshots, live update samples, screeners,
historical bars, option discovery and chains, news, research sections, and
economic or corporate calendars.

Importing tvfinance does not import FastMCP. Attempting to start the server
without the extra raises an actionable installation error.
