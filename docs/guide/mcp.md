# MCP server

MCP is optional and uses the shared async API rather than a separate
implementation.

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
