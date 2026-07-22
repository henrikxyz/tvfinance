from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tvfinance.core import (
    CalendarEvent,
    Candle,
    NewsArticle,
    OptionChainRow,
    OptionSeries,
    Quote,
    ResearchData,
    ScreenerRow,
    Symbol,
    SymbolSearchResult,
)
from tvfinance.core.cache import MemoryResponseCache, SQLiteResponseCache
from tvfinance.core.exceptions import OptionalDependencyError, ValidationError
from tvfinance.mcp import (
    MCP_INSTRUCTIONS,
    TOOLS,
    McpService,
    build_parser,
    create_server,
    get_corporate_calendar,
    get_economic_calendar,
    get_histories,
    get_history,
    get_news,
    get_news_for_symbols,
    get_news_markdown,
    get_option_series,
    get_options_chain,
    get_quote,
    get_quote_updates,
    get_quotes,
    get_research,
    get_research_for_symbols,
    main,
    query_screener,
    search_symbols,
)

NOW = datetime(2026, 7, 22, tzinfo=timezone.utc)
SYMBOL = Symbol("NASDAQ", "AAPL")
QUOTE = Quote(SYMBOL, last=200)


class FakeClient:
    def __init__(self, **kwargs: Any) -> None:
        self.init_kwargs = kwargs
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.closed = False

    async def __aenter__(self) -> FakeClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        self.closed = True

    def record(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((name, args, kwargs))

    async def search(self, query: str) -> list[SymbolSearchResult]:
        self.record("search", query)
        return [SymbolSearchResult(SYMBOL, query)]

    async def quote(self, symbol: str) -> Quote:
        self.record("quote", symbol)
        return QUOTE

    async def quotes(self, symbols: list[str | Symbol]) -> dict[str, Quote | None]:
        self.record("quotes", symbols)
        return {str(symbols[0]): QUOTE, str(symbols[1]): None}

    async def screener(self, **kwargs: Any) -> list[ScreenerRow]:
        self.record("screener", **kwargs)
        return [ScreenerRow(SYMBOL, {"limit": kwargs["limit"]})]

    async def options_chain(
        self, symbol: str, *, expiration: int | None, root: str | None
    ) -> list[OptionChainRow]:
        self.record("options_chain", symbol, expiration=expiration, root=root)
        return [OptionChainRow(200)]

    async def option_series(self, symbol: str) -> list[OptionSeries]:
        self.record("option_series", symbol)
        return [OptionSeries("AAPL", 1_798_761_600)]

    async def history(
        self,
        symbol: str | Symbol,
        *,
        resolution: str,
        count: int | str | None,
        adjustment: str,
    ) -> list[Candle]:
        self.record(
            "history",
            symbol,
            resolution=resolution,
            count=count,
            adjustment=adjustment,
        )
        return [Candle(SYMBOL, NOW, 1, 2, 0, 1.5)]

    async def research(self, symbol: str | Symbol, section: str) -> ResearchData:
        self.record("research", symbol, section)
        return ResearchData(SYMBOL, section)

    async def corporate_calendar(
        self,
        category: str,
        *,
        from_date: datetime | None,
        to_date: datetime | None,
        limit: int,
    ) -> list[CalendarEvent]:
        self.record(
            "corporate_calendar",
            category,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )
        return [CalendarEvent("e", category, NOW, category)]

    async def news(
        self,
        symbol: str | Symbol,
        *,
        limit: int,
        language: str | None,
        fetch_body: bool,
    ) -> list[NewsArticle]:
        self.record(
            "news",
            symbol,
            limit=limit,
            language=language,
            fetch_body=fetch_body,
        )
        return [NewsArticle("n", "Title", NOW)]

    async def news_markdown(
        self, symbol: str, *, limit: int, language: str | None
    ) -> str:
        self.record("news_markdown", symbol, limit=limit, language=language)
        return "# News"

    async def stream_quotes(self, symbols: list[str | Symbol]) -> Any:
        self.record("stream_quotes", symbols)
        yield QUOTE
        yield QUOTE

    async def economic_calendar(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        countries: list[str] | None,
        importance: int | list[int] | None,
    ) -> list[CalendarEvent]:
        self.record(
            "economic_calendar",
            from_date=from_date,
            to_date=to_date,
            countries=countries,
            importance=importance,
        )
        return [CalendarEvent("e", "Event", from_date, "economic")]


class FakeServer:
    def __init__(self, name: str, **kwargs: Any) -> None:
        self.name = name
        self.kwargs = kwargs
        self.tools: list[tuple[Any, dict[str, Any]]] = []
        self.run_kwargs: dict[str, Any] | None = None

    def tool(self, function: Any, **kwargs: Any) -> Any:
        self.tools.append((function, kwargs))
        return function

    def run(self, **kwargs: Any) -> None:
        self.run_kwargs = kwargs


@pytest.mark.asyncio
async def test_service_exposes_complete_client_surface() -> None:
    client = FakeClient()
    service = McpService(cast(Any, client))

    assert (await service.search_symbols("Apple"))[0]["description"] == "Apple"
    assert (await service.get_quote("NASDAQ:AAPL"))["last"] == 200
    assert (await service.get_quotes(["NASDAQ:AAPL", "NASDAQ:MSFT"]))[
        "NASDAQ:MSFT"
    ] is None
    assert (await service.query_screener("crypto", ["close"], 7, "close", "asc"))[0][
        "values"
    ] == {"limit": 7}
    assert (await service.get_options_chain("NASDAQ:AAPL", 123, "AAPL"))[0][
        "strike"
    ] == 200
    assert (await service.get_option_series("NASDAQ:AAPL"))[0]["root"] == "AAPL"
    assert (await service.get_history("NASDAQ:AAPL", "60", "max", "none"))[0][
        "close"
    ] == 1.5
    assert (await service.get_histories(["NASDAQ:AAPL", "NASDAQ:MSFT"], count=5))[
        "NASDAQ:AAPL"
    ][0]["close"] == 1.5
    assert (await service.get_research("NASDAQ:AAPL", "profile"))["section"] == (
        "profile"
    )
    assert (
        await service.get_research_for_symbols(
            ["NASDAQ:AAPL", "NASDAQ:MSFT"], "forecast"
        )
    )["NASDAQ:MSFT"]["section"] == "forecast"
    assert (
        await service.get_corporate_calendar("earnings", "2026-07-01", "2026-07-31", 9)
    )[0]["category"] == "earnings"
    assert (await service.get_corporate_calendar("ipo", None, None, 2))[0][
        "category"
    ] == "ipo"
    assert (await service.get_news("NASDAQ:AAPL", 3, "zh", True))[0]["title"] == "Title"
    assert (
        await service.get_news_for_symbols(
            ["NASDAQ:AAPL", "NASDAQ:MSFT"], 2, "en", False
        )
    )["NASDAQ:MSFT"][0]["title"] == "Title"
    assert await service.get_news_markdown("NASDAQ:AAPL", 1, "en") == "# News"
    assert len(await service.get_quote_updates(["NASDAQ:AAPL"], 2)) == 2
    assert await service.get_quote_updates(["NASDAQ:AAPL"], 0) == []

    async def empty_stream(symbols: list[str | Symbol]) -> Any:
        del symbols
        for item in cast(list[Quote], []):
            yield item

    client.stream_quotes = empty_stream  # type: ignore[method-assign]
    assert await service.get_quote_updates(["NASDAQ:AAPL"], 1) == []
    assert (
        await service.get_economic_calendar(
            "2026-07-22", "2026-07-23T12:00:00", ["US"], [1, 2]
        )
    )[0]["title"] == "Event"

    assert any(call[0] == "screener" for call in client.calls)
    assert any(call[0] == "economic_calendar" for call in client.calls)


@pytest.mark.asyncio
async def test_module_wrappers_use_scoped_clients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[FakeClient] = []

    def factory(**kwargs: Any) -> FakeClient:
        client = FakeClient(**kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr("tvfinance.mcp.AsyncClient", factory)
    assert (await search_symbols("Apple"))[0]["description"] == "Apple"
    assert (await get_quote("NASDAQ:AAPL"))["last"] == 200
    assert (await get_quotes(["NASDAQ:AAPL", "NASDAQ:MSFT"]))["NASDAQ:MSFT"] is None
    assert (await query_screener(limit=1))[0]["values"] == {"limit": 1}
    assert (await get_options_chain("NASDAQ:AAPL"))[0]["strike"] == 200
    assert (await get_option_series("NASDAQ:AAPL"))[0]["root"] == "AAPL"
    assert (await get_history("NASDAQ:AAPL"))[0]["close"] == 1.5
    assert (await get_histories(["NASDAQ:AAPL"]))["NASDAQ:AAPL"]
    assert (await get_research("NASDAQ:AAPL", "profile"))["section"] == "profile"
    assert (await get_research_for_symbols(["NASDAQ:AAPL"], "forecast"))["NASDAQ:AAPL"][
        "section"
    ] == "forecast"
    assert (await get_corporate_calendar("earnings"))[0]["category"] == "earnings"
    assert (await get_news("NASDAQ:AAPL"))[0]["title"] == "Title"
    assert (await get_news_for_symbols(["NASDAQ:AAPL"]))["NASDAQ:AAPL"]
    assert await get_news_markdown("NASDAQ:AAPL") == "# News"
    assert len(await get_quote_updates(["NASDAQ:AAPL"], 2)) == 2
    assert await get_quote_updates(["NASDAQ:AAPL"], 0) == []
    assert (await get_economic_calendar("2026-07-22", "2026-07-23"))[0][
        "title"
    ] == "Event"
    assert clients and all(client.closed for client in clients)


@pytest.mark.asyncio
async def test_validation_rejects_unsupported_mcp_requests() -> None:
    service = McpService(cast(Any, FakeClient()))
    for invalid in (0, 31):
        with pytest.raises(ValidationError, match="between 1 and 30"):
            await service.get_news("NASDAQ:AAPL", invalid)
        with pytest.raises(ValidationError, match="between 1 and 30"):
            await service.get_news_for_symbols(["NASDAQ:AAPL"], invalid)
        with pytest.raises(ValidationError, match="between 1 and 30"):
            await service.get_news_markdown("NASDAQ:AAPL", invalid)
    with pytest.raises(ValidationError, match="At least one symbol is required"):
        await service.get_histories([])


def test_create_server_registers_described_read_only_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = SimpleNamespace(FastMCP=FakeServer)
    monkeypatch.setattr("tvfinance.mcp.import_module", lambda name: module)
    server = create_server()
    assert server.name == "tvfinance"
    assert server.kwargs["instructions"] == MCP_INSTRUCTIONS
    assert server.kwargs["mask_error_details"] is True
    assert len(server.tools) == len(TOOLS) == 16
    assert {options["name"] for _, options in server.tools} == {
        tool.__name__ for tool in TOOLS
    }
    for _, options in server.tools:
        assert options["title"]
        assert options["description"]
        assert options["annotations"]["readOnlyHint"] is True


def test_missing_mcp_extra_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(name: str) -> Any:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("tvfinance.mcp.import_module", missing)
    with pytest.raises(OptionalDependencyError, match=r"tvfinance\[mcp\]"):
        create_server()


@pytest.mark.asyncio
async def test_real_fastmcp_handshake_and_lifespan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastmcp import Client

    client = FakeClient()
    monkeypatch.setattr("tvfinance.mcp.AsyncClient", lambda **kwargs: client)
    server = create_server()
    async with Client(server) as protocol:
        tools = await protocol.list_tools()
        assert len(tools) == 16
        assert all(
            tool.description and tool.title and tool.annotations for tool in tools
        )
        result = await protocol.call_tool(
            "get_quote_updates", {"symbols": ["NASDAQ:AAPL"], "updates": 0}
        )
        assert result.data == []
    assert client.closed is True


def test_parser_and_stdio_main(monkeypatch: pytest.MonkeyPatch) -> None:
    assert build_parser().parse_args([]).transport == "stdio"
    server = FakeServer("tvfinance")
    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeServer:
        captured.update(kwargs)
        return server

    monkeypatch.setattr("tvfinance.mcp.create_server", factory)
    assert main(["--memory-cache", "--cache-ttl", "12", "--no-banner"]) == 0
    assert isinstance(captured["cache"], MemoryResponseCache)
    assert captured["settings"].timeout == 30
    assert server.run_kwargs == {
        "transport": "stdio",
        "show_banner": False,
    }
    assert main([]) == 0


def test_streamable_http_main_and_sqlite_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    server = FakeServer("tvfinance")
    captured: dict[str, Any] = {}

    def factory(**kwargs: Any) -> FakeServer:
        captured.update(kwargs)
        return server

    monkeypatch.setattr("tvfinance.mcp.create_server", factory)
    cache_path = tmp_path / "mcp.sqlite3"
    assert (
        main(
            [
                "--transport",
                "streamable-http",
                "--host",
                "0.0.0.0",
                "--allow-network",
                "--port",
                "9000",
                "--path",
                "/custom",
                "--timeout",
                "8",
                "--language",
                "zh",
                "--region",
                "TW",
                "--retry-attempts",
                "4",
                "--retry-base-delay",
                "1",
                "--retry-maximum-delay",
                "9",
                "--cache-path",
                str(cache_path),
                "--cache-max-entries",
                "42",
            ]
        )
        == 0
    )
    assert isinstance(captured["cache"], SQLiteResponseCache)
    settings = captured["settings"]
    assert (settings.timeout, settings.locale.language, settings.locale.region) == (
        8,
        "zh",
        "TW",
    )
    assert settings.retry.attempts == 4
    assert server.run_kwargs == {
        "transport": "streamable-http",
        "show_banner": True,
        "host": "0.0.0.0",
        "port": 9000,
        "path": "/custom",
    }


def test_http_main_rejects_accidental_network_exposure() -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--transport", "streamable-http", "--host", "0.0.0.0"])
    assert exc_info.value.code == 2
