"""Optional MCP server backed by the complete tvfinance client surface."""

from __future__ import annotations

import argparse
import asyncio
import inspect
from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from importlib import import_module
from pathlib import Path
from typing import Any, Literal, cast

from tvfinance.client import AsyncClient
from tvfinance.core.cache import MemoryResponseCache, ResponseCache, SQLiteResponseCache
from tvfinance.core.exceptions import OptionalDependencyError
from tvfinance.core.models import Symbol
from tvfinance.core.settings import ClientSettings, Locale, RetryPolicy
from tvfinance.core.validation import normalize_symbols

ResearchSection = Literal[
    "bonds",
    "etfs",
    "documents",
    "holdings",
    "ideas",
    "financials",
    "forecast",
    "technicals",
    "profile",
]
CalendarCategory = Literal["earnings", "revenue", "dividends", "ipo"]
SortOrder = Literal["asc", "desc"]
HistoryCount = int | Literal["max"] | None
McpTransport = Literal["stdio", "streamable-http"]

MCP_INSTRUCTIONS = """
TVFinance provides read-only, unofficial market-data research tools. Symbols must
use EXCHANGE:NAME, for example NASDAQ:AAPL. Use search_symbols before guessing a
symbol. Dates use ISO 8601. Results may be delayed, incomplete, or incorrect and
are not financial advice. TradingView access does not grant rights to automate,
process, store, or redistribute provider data; the operator must establish all
required permissions. Prefer small bounded requests. News is a latest-news
snapshot limited to 30 items, not a historical archive. Never use these tools to
place trades or make autonomous financial decisions.
""".strip()

READ_ONLY_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


def _serialize(items: list[Any]) -> list[dict[str, Any]]:
    return [cast(dict[str, Any], item.to_dict()) for item in items]


class McpService:
    """Complete MCP-facing operations sharing one configured async client."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def search_symbols(self, query: str) -> list[dict[str, Any]]:
        """Search for provider symbols before using market-data tools.

        Args:
            query: Company, asset, or ticker text such as ``Apple``.

        Returns:
            Matches containing symbol, description, asset type, currency, and
            provider identifier when available.
        """
        return _serialize(await self.client.search(query))

    async def get_quote(self, symbol: str) -> dict[str, Any]:
        """Get one current quote snapshot for an exchange-qualified symbol.

        Args:
            symbol: Symbol in ``EXCHANGE:NAME`` form, such as ``NASDAQ:AAPL``.

        Returns:
            Quote fields including last, change, OHLC, volume, bid, ask,
            currency, and provider timestamp. Unavailable fields are null.
        """
        return cast(dict[str, Any], (await self.client.quote(symbol)).to_dict())

    async def get_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any] | None]:
        """Get current quote snapshots for several qualified symbols at once.

        Args:
            symbols: Non-empty list of unique ``EXCHANGE:NAME`` symbols.

        Returns:
            Mapping from normalized symbol to quote data or null when the
            provider did not return that symbol.
        """
        result = await self.client.quotes(cast(list[str | Symbol], symbols))
        return {
            symbol: cast(dict[str, Any], quote.to_dict()) if quote else None
            for symbol, quote in result.items()
        }

    async def query_screener(
        self,
        market: str = "america",
        columns: list[str] | None = None,
        limit: int = 50,
        sort_by: str = "market_cap_basic",
        sort_order: SortOrder = "desc",
    ) -> list[dict[str, Any]]:
        """Query a market screener with explicit columns and ordering.

        Args:
            market: Provider market such as ``america``, ``crypto``, or ``forex``.
            columns: Provider column names; omit for the standard quote columns.
            limit: Positive maximum number of rows.
            sort_by: Provider column used for ordering.
            sort_order: ``asc`` or ``desc``.

        Returns:
            Rows containing a qualified symbol and a values mapping keyed by
            the requested columns.
        """
        return _serialize(
            await self.client.screener(
                market=market,
                columns=columns,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        )

    async def get_options_chain(
        self,
        symbol: str,
        expiration: int | None = None,
        root: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get paired call and put contracts by strike.

        Args:
            symbol: Underlying in ``EXCHANGE:NAME`` form.
            expiration: Provider Unix expiration timestamp. Obtain it from
                ``get_option_series`` for deterministic selection.
            root: Option root returned by ``get_option_series``.

        Returns:
            Strike rows containing optional call and put contracts with prices
            and Greeks. When root or expiration is omitted, the first matching
            series is selected.
        """
        return _serialize(
            await self.client.options_chain(symbol, expiration=expiration, root=root)
        )

    async def get_option_series(self, symbol: str) -> list[dict[str, Any]]:
        """List selectable option roots and expiration timestamps.

        Args:
            symbol: Underlying in ``EXCHANGE:NAME`` form.

        Returns:
            Available ``root`` and Unix ``expiration`` pairs.
        """
        return _serialize(await self.client.option_series(symbol))

    async def get_history(
        self,
        symbol: str,
        resolution: str = "1D",
        count: HistoryCount = 300,
        adjustment: str = "splits",
    ) -> list[dict[str, Any]]:
        """Get OHLCV history for one qualified symbol.

        Args:
            symbol: Symbol in ``EXCHANGE:NAME`` form.
            resolution: Provider timeframe such as ``1``, ``60``, ``1D``, or ``1W``.
            count: Positive bar count, ``max`` for up to 50,000, or null for 300.
            adjustment: Provider adjustment mode, normally ``splits``.

        Returns:
            Chronological candles with timestamp, open, high, low, close, and
            optional volume.
        """
        return _serialize(
            await self.client.history(
                symbol,
                resolution=resolution,
                count=count,
                adjustment=adjustment,
            )
        )

    async def get_histories(
        self,
        symbols: list[str],
        resolution: str = "1D",
        count: HistoryCount = 300,
        adjustment: str = "splits",
    ) -> dict[str, list[dict[str, Any]]]:
        """Get OHLCV history concurrently for several symbols.

        Args:
            symbols: Non-empty list of ``EXCHANGE:NAME`` symbols.
            resolution: Provider timeframe such as ``1D``.
            count: Positive bar count, ``max``, or null for 300.
            adjustment: Provider adjustment mode, normally ``splits``.

        Returns:
            Mapping from each input symbol to its chronological candle list.
        """
        normalized = normalize_symbols(symbols)
        values = await asyncio.gather(
            *(
                self.client.history(
                    symbol,
                    resolution=resolution,
                    count=count,
                    adjustment=adjustment,
                )
                for symbol in normalized
            )
        )
        return {
            symbol.ticker: _serialize(value)
            for symbol, value in zip(normalized, values, strict=True)
        }

    async def get_research(
        self, symbol: str, section: ResearchSection
    ) -> dict[str, Any]:
        """Get one normalized research section for a symbol.

        Args:
            symbol: Symbol in ``EXCHANGE:NAME`` form.
            section: One of profile, financials, forecast, technicals, holdings,
                ideas, documents, bonds, or etfs.

        Returns:
            Symbol, section, normalized records, and summary values.
        """
        return cast(
            dict[str, Any], (await self.client.research(symbol, section)).to_dict()
        )

    async def get_research_for_symbols(
        self, symbols: list[str], section: ResearchSection
    ) -> dict[str, dict[str, Any]]:
        """Get the same research section concurrently for several symbols.

        Args:
            symbols: Non-empty list of ``EXCHANGE:NAME`` symbols.
            section: Supported research section shared by every request.

        Returns:
            Mapping from symbol to normalized research data.
        """
        normalized = normalize_symbols(symbols)
        values = await asyncio.gather(
            *(self.client.research(symbol, section) for symbol in normalized)
        )
        return {
            symbol.ticker: cast(dict[str, Any], value.to_dict())
            for symbol, value in zip(normalized, values, strict=True)
        }

    async def get_corporate_calendar(
        self,
        category: CalendarCategory,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get corporate earnings, revenue, dividend, or IPO events.

        Args:
            category: ``earnings``, ``revenue``, ``dividends``, or ``ipo``.
            from_date: Optional ISO 8601 start date or datetime; defaults to yesterday.
            to_date: Optional ISO 8601 end date or datetime; defaults to seven
                days ahead.
            limit: Positive maximum number of events.

        Returns:
            Normalized calendar events with timestamps, symbols, reported and
            estimated values when available.
        """
        return _serialize(
            await self.client.corporate_calendar(
                category,
                from_date=_optional_datetime(from_date),
                to_date=_optional_datetime(to_date),
                limit=limit,
            )
        )

    async def get_news(
        self,
        symbol: str,
        limit: int = 10,
        language: str | None = None,
        fetch_body: bool = False,
    ) -> list[dict[str, Any]]:
        """Get the latest news snapshot for a symbol.

        Args:
            symbol: Symbol in ``EXCHANGE:NAME`` form.
            limit: Number of latest items from 1 through 30; no history
                pagination exists.
            language: Optional provider language code such as ``en``.
            fetch_body: Fetch and convert each available article body to Markdown.

        Returns:
            News metadata and optional ``body_markdown``. This is not a complete
            historical archive.
        """
        _validate_news_limit(limit)
        return _serialize(
            await self.client.news(
                symbol,
                limit=limit,
                language=language,
                fetch_body=fetch_body,
            )
        )

    async def get_news_for_symbols(
        self,
        symbols: list[str],
        limit: int = 10,
        language: str | None = None,
        fetch_body: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get latest news snapshots concurrently for several symbols.

        Args:
            symbols: Non-empty list of ``EXCHANGE:NAME`` symbols.
            limit: Per-symbol item count from 1 through 30.
            language: Optional provider language code.
            fetch_body: Fetch article bodies as Markdown when available.

        Returns:
            Mapping from symbol to its latest-news snapshot.
        """
        _validate_news_limit(limit)
        normalized = normalize_symbols(symbols)
        values = await asyncio.gather(
            *(
                self.client.news(
                    symbol,
                    limit=limit,
                    language=language,
                    fetch_body=fetch_body,
                )
                for symbol in normalized
            )
        )
        return {
            symbol.ticker: _serialize(value)
            for symbol, value in zip(normalized, values, strict=True)
        }

    async def get_news_markdown(
        self,
        symbol: str,
        limit: int = 10,
        language: str | None = None,
    ) -> str:
        """Fetch latest articles and render them as one Markdown document.

        Args:
            symbol: Symbol in ``EXCHANGE:NAME`` form.
            limit: Number of latest items from 1 through 30.
            language: Optional provider language code.

        Returns:
            Article metadata and bodies separated by Markdown rules.
        """
        _validate_news_limit(limit)
        return await self.client.news_markdown(symbol, limit=limit, language=language)

    async def get_quote_updates(
        self, symbols: list[str], updates: int = 1
    ) -> list[dict[str, Any]]:
        """Collect a bounded sample from the live quote stream.

        Args:
            symbols: Non-empty list of ``EXCHANGE:NAME`` symbols.
            updates: Positive number of updates to collect before returning;
                zero returns immediately without opening a stream.

        Returns:
            Up to the requested number of quote updates. This bounded MCP call
            is not a permanent subscription.
        """
        if updates <= 0:
            return []
        result: list[dict[str, Any]] = []
        async for quote in self.client.stream_quotes(cast(list[str | Symbol], symbols)):
            result.append(cast(dict[str, Any], quote.to_dict()))
            if len(result) >= updates:
                break
        return result

    async def get_economic_calendar(
        self,
        from_date: str,
        to_date: str,
        countries: list[str] | None = None,
        importance: int | list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Get economic events in an explicit ISO 8601 date range.

        Args:
            from_date: Inclusive ISO 8601 start date or datetime.
            to_date: Inclusive ISO 8601 end date or datetime.
            countries: Optional provider country codes such as ``US``.
            importance: Optional importance value or list of values to retain.

        Returns:
            Normalized economic events with actual, estimate, and previous values.
        """
        return _serialize(
            await self.client.economic_calendar(
                from_date=datetime.fromisoformat(from_date),
                to_date=datetime.fromisoformat(to_date),
                countries=countries,
                importance=importance,
            )
        )


def _optional_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _validate_news_limit(limit: int) -> None:
    if not 1 <= limit <= 30:
        from tvfinance.core.exceptions import ValidationError

        raise ValidationError(
            "news limit must be between 1 and 30",
            context={"limit": limit},
        )


async def search_symbols(query: str) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).search_symbols(query)


async def get_quote(symbol: str) -> dict[str, Any]:
    async with AsyncClient() as client:
        return await McpService(client).get_quote(symbol)


async def get_quotes(symbols: list[str]) -> dict[str, dict[str, Any] | None]:
    async with AsyncClient() as client:
        return await McpService(client).get_quotes(symbols)


async def query_screener(
    market: str = "america",
    columns: list[str] | None = None,
    limit: int = 50,
    sort_by: str = "market_cap_basic",
    sort_order: SortOrder = "desc",
) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).query_screener(
            market, columns, limit, sort_by, sort_order
        )


async def get_options_chain(
    symbol: str, expiration: int | None = None, root: str | None = None
) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).get_options_chain(symbol, expiration, root)


async def get_option_series(symbol: str) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).get_option_series(symbol)


async def get_history(
    symbol: str,
    resolution: str = "1D",
    count: HistoryCount = 300,
    adjustment: str = "splits",
) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).get_history(
            symbol, resolution, count, adjustment
        )


async def get_histories(
    symbols: list[str],
    resolution: str = "1D",
    count: HistoryCount = 300,
    adjustment: str = "splits",
) -> dict[str, list[dict[str, Any]]]:
    async with AsyncClient() as client:
        return await McpService(client).get_histories(
            symbols, resolution, count, adjustment
        )


async def get_research(symbol: str, section: ResearchSection) -> dict[str, Any]:
    async with AsyncClient() as client:
        return await McpService(client).get_research(symbol, section)


async def get_research_for_symbols(
    symbols: list[str], section: ResearchSection
) -> dict[str, dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).get_research_for_symbols(symbols, section)


async def get_corporate_calendar(
    category: CalendarCategory,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).get_corporate_calendar(
            category, from_date, to_date, limit
        )


async def get_news(
    symbol: str,
    limit: int = 10,
    language: str | None = None,
    fetch_body: bool = False,
) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).get_news(symbol, limit, language, fetch_body)


async def get_news_for_symbols(
    symbols: list[str],
    limit: int = 10,
    language: str | None = None,
    fetch_body: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    async with AsyncClient() as client:
        return await McpService(client).get_news_for_symbols(
            symbols, limit, language, fetch_body
        )


async def get_news_markdown(
    symbol: str, limit: int = 10, language: str | None = None
) -> str:
    async with AsyncClient() as client:
        return await McpService(client).get_news_markdown(symbol, limit, language)


async def get_quote_updates(
    symbols: list[str], updates: int = 1
) -> list[dict[str, Any]]:
    if updates <= 0:
        return []
    async with AsyncClient() as client:
        return await McpService(client).get_quote_updates(symbols, updates)


async def get_economic_calendar(
    from_date: str,
    to_date: str,
    countries: list[str] | None = None,
    importance: int | list[int] | None = None,
) -> list[dict[str, Any]]:
    async with AsyncClient() as client:
        return await McpService(client).get_economic_calendar(
            from_date, to_date, countries, importance
        )


TOOLS = (
    search_symbols,
    get_quote,
    get_quotes,
    query_screener,
    get_options_chain,
    get_option_series,
    get_history,
    get_histories,
    get_research,
    get_research_for_symbols,
    get_corporate_calendar,
    get_news_markdown,
    get_quote_updates,
    get_news,
    get_news_for_symbols,
    get_economic_calendar,
)

TOOL_TITLES = {
    "search_symbols": "Search symbols",
    "get_quote": "Get quote",
    "get_quotes": "Get quotes",
    "query_screener": "Query market screener",
    "get_options_chain": "Get options chain",
    "get_option_series": "List option series",
    "get_history": "Get price history",
    "get_histories": "Get price histories",
    "get_research": "Get symbol research",
    "get_research_for_symbols": "Get research for symbols",
    "get_corporate_calendar": "Get corporate calendar",
    "get_news_markdown": "Get news as Markdown",
    "get_quote_updates": "Sample live quote updates",
    "get_news": "Get latest news",
    "get_news_for_symbols": "Get latest news for symbols",
    "get_economic_calendar": "Get economic calendar",
}


def create_server(
    *,
    settings: ClientSettings | None = None,
    cache: ResponseCache | None = None,
) -> Any:
    """Create a configured FastMCP server with a shared async client."""
    try:
        fastmcp = import_module("fastmcp")
    except ModuleNotFoundError as exc:
        raise OptionalDependencyError("mcp") from exc

    client = AsyncClient(settings=settings, cache=cache)
    service = McpService(client)

    @asynccontextmanager
    async def lifespan(server: Any) -> Any:
        del server
        try:
            yield {"client": client}
        finally:
            await client.close()

    server = fastmcp.FastMCP(
        "tvfinance",
        instructions=MCP_INSTRUCTIONS,
        lifespan=lifespan,
        mask_error_details=True,
        strict_input_validation=True,
    )
    for name in TOOL_TITLES:
        function = cast(Callable[..., Any], getattr(service, name))
        server.tool(
            function,
            name=name,
            title=TOOL_TITLES[name],
            description=inspect.getdoc(function),
            annotations=READ_ONLY_ANNOTATIONS,
        )
    return server


def build_parser() -> argparse.ArgumentParser:
    """Build command-line options for stdio and Streamable HTTP servers."""
    parser = argparse.ArgumentParser(prog="tvfinance-mcp")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--language", default="en")
    parser.add_argument("--region", default="US")
    parser.add_argument("--retry-attempts", type=int, default=3)
    parser.add_argument("--retry-base-delay", type=float, default=0.5)
    parser.add_argument("--retry-maximum-delay", type=float, default=8.0)
    cache_group = parser.add_mutually_exclusive_group()
    cache_group.add_argument("--memory-cache", action="store_true")
    cache_group.add_argument("--cache-path", type=Path)
    parser.add_argument("--cache-ttl", type=float, default=3600.0)
    parser.add_argument("--cache-max-entries", type=int, default=10_000)
    parser.add_argument("--no-banner", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the configured MCP server."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if (
        args.transport == "streamable-http"
        and args.host not in {"127.0.0.1", "localhost", "::1"}
        and not args.allow_network
    ):
        parser.error("non-loopback HTTP binding requires --allow-network")
    settings = ClientSettings(
        timeout=args.timeout,
        locale=Locale(args.language, args.region),
        retry=RetryPolicy(
            attempts=args.retry_attempts,
            base_delay=args.retry_base_delay,
            maximum_delay=args.retry_maximum_delay,
        ),
    )
    cache: ResponseCache | None = None
    if args.memory_cache:
        cache = MemoryResponseCache(ttl=args.cache_ttl)
    elif args.cache_path is not None:
        cache = SQLiteResponseCache(
            args.cache_path,
            ttl=args.cache_ttl,
            max_entries=args.cache_max_entries,
        )
    server = create_server(settings=settings, cache=cache)
    run_kwargs: dict[str, Any] = {}
    if args.transport == "streamable-http":
        run_kwargs = {"host": args.host, "port": args.port, "path": args.path}
    server.run(
        transport=cast(McpTransport, args.transport),
        show_banner=not args.no_banner,
        **run_kwargs,
    )
    return 0


__all__ = [
    "MCP_INSTRUCTIONS",
    "TOOLS",
    "McpService",
    "build_parser",
    "create_server",
    "get_corporate_calendar",
    "get_economic_calendar",
    "get_histories",
    "get_history",
    "get_news",
    "get_news_for_symbols",
    "get_news_markdown",
    "get_option_series",
    "get_options_chain",
    "get_quote",
    "get_quote_updates",
    "get_quotes",
    "get_research",
    "get_research_for_symbols",
    "main",
    "query_screener",
    "search_symbols",
]
