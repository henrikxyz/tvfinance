"""Optional MCP server backed by the shared tvfinance domain API."""

from __future__ import annotations

from datetime import datetime
from importlib import import_module
from typing import Any, cast

from tvfinance import aio
from tvfinance.core.exceptions import OptionalDependencyError
from tvfinance.core.models import Symbol


async def search_symbols(query: str) -> list[dict[str, Any]]:
    return [item.to_dict() for item in await aio.search(query)]


async def get_quote(symbol: str) -> dict[str, Any]:
    return (await aio.quote(symbol)).to_dict()


async def get_quotes(symbols: list[str]) -> dict[str, dict[str, Any] | None]:
    result = await aio.quotes(cast(list[str | Symbol], symbols))
    return {
        symbol: quote.to_dict() if quote is not None else None
        for symbol, quote in result.items()
    }


async def query_screener(
    market: str = "america", limit: int = 20
) -> list[dict[str, Any]]:
    return [item.to_dict() for item in await aio.screener(market=market, limit=limit)]


async def get_options_chain(
    symbol: str, expiration: int, root: str
) -> list[dict[str, Any]]:
    return [
        item.to_dict()
        for item in await aio.options_chain(symbol, expiration=expiration, root=root)
    ]


async def get_news(symbol: str, limit: int = 10) -> list[dict[str, Any]]:
    return [item.to_dict() for item in await aio.news(symbol, limit=limit)]


async def get_economic_calendar(
    from_date: str,
    to_date: str,
    countries: list[str] | None = None,
) -> list[dict[str, Any]]:
    return [
        item.to_dict()
        for item in await aio.economic_calendar(
            from_date=datetime.fromisoformat(from_date),
            to_date=datetime.fromisoformat(to_date),
            countries=countries,
        )
    ]


TOOLS = (
    search_symbols,
    get_quote,
    get_quotes,
    query_screener,
    get_options_chain,
    get_news,
    get_economic_calendar,
)


def create_server() -> Any:
    """Create the FastMCP server after verifying the optional dependency."""
    try:
        fastmcp = import_module("fastmcp")
    except ModuleNotFoundError as exc:
        raise OptionalDependencyError("mcp") from exc
    server = fastmcp.FastMCP("tvfinance")
    for tool in TOOLS:
        server.tool(tool)
    return server


def main() -> int:
    create_server().run()
    return 0


__all__ = ["TOOLS", "create_server", "main"]
