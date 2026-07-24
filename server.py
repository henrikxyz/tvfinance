"""Repository-level entrypoint for the TVFinance MCP server."""

from tvfinance.mcp import create_server

mcp = create_server()
