from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from tvfinance import aio
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
from tvfinance.core.exceptions import OptionalDependencyError
from tvfinance.mcp import (
    TOOLS,
    create_server,
    get_corporate_calendar,
    get_economic_calendar,
    get_history,
    get_news,
    get_news_markdown,
    get_option_series,
    get_options_chain,
    get_quote,
    get_quote_updates,
    get_quotes,
    get_research,
    main,
    query_screener,
    search_symbols,
)


class FakeServer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: list[Any] = []
        self.ran = False

    def tool(self, function: Any) -> Any:
        self.tools.append(function)
        return function

    def run(self) -> None:
        self.ran = True


def test_create_server_registers_shared_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    module = SimpleNamespace(FastMCP=FakeServer)
    monkeypatch.setattr("tvfinance.mcp.import_module", lambda name: module)
    server = create_server()
    assert server.name == "tvfinance"
    assert tuple(server.tools) == TOOLS


def test_missing_mcp_extra_has_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(name: str) -> Any:
        raise ModuleNotFoundError(name)

    monkeypatch.setattr("tvfinance.mcp.import_module", missing)
    with pytest.raises(OptionalDependencyError, match=r"tvfinance\[mcp\]"):
        create_server()


def test_mcp_main_runs_server(monkeypatch: pytest.MonkeyPatch) -> None:
    server = FakeServer("tvfinance")
    monkeypatch.setattr("tvfinance.mcp.create_server", lambda: server)
    assert main() == 0
    assert server.ran is True


@pytest.mark.asyncio
async def test_mcp_tools_delegate_to_async_namespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    symbol = Symbol("NASDAQ", "AAPL")
    quote = Quote(symbol, last=200)

    async def fake_search(query: str) -> list[SymbolSearchResult]:
        return [SymbolSearchResult(symbol, query)]

    async def fake_quote(value: str) -> Quote:
        return quote

    async def fake_quotes(values: list[str]) -> dict[str, Quote | None]:
        return {values[0]: quote, values[1]: None}

    async def fake_screener(**kwargs: Any) -> list[ScreenerRow]:
        return [ScreenerRow(symbol, {"limit": kwargs["limit"]})]

    async def fake_options(*args: Any, **kwargs: Any) -> list[OptionChainRow]:
        return [OptionChainRow(200)]

    async def fake_news(*args: Any, **kwargs: Any) -> list[NewsArticle]:
        from datetime import datetime, timezone

        return [NewsArticle("n", "Title", datetime.now(timezone.utc))]

    async def fake_calendar(**kwargs: Any) -> list[CalendarEvent]:
        return [CalendarEvent("e", "Event", kwargs["from_date"], "economic")]

    async def fake_series(value: str) -> list[OptionSeries]:
        return [OptionSeries("AAPL", 20261218)]

    async def fake_history(*args: Any, **kwargs: Any) -> list[Candle]:
        from datetime import datetime, timezone

        return [Candle(symbol, datetime.now(timezone.utc), 1, 2, 0, 1.5)]

    async def fake_research(value: str, section: str) -> ResearchData:
        return ResearchData(symbol, section)

    async def fake_corporate(category: str, **kwargs: Any) -> list[CalendarEvent]:
        from datetime import datetime, timezone

        return [CalendarEvent("e", category, datetime.now(timezone.utc), category)]

    async def fake_markdown(*args: Any, **kwargs: Any) -> str:
        return "# News"

    async def fake_stream(values: list[str]) -> Any:
        yield quote

    monkeypatch.setattr(aio, "search", fake_search)
    monkeypatch.setattr(aio, "quote", fake_quote)
    monkeypatch.setattr(aio, "quotes", fake_quotes)
    monkeypatch.setattr(aio, "screener", fake_screener)
    monkeypatch.setattr(aio, "options_chain", fake_options)
    monkeypatch.setattr(aio, "news", fake_news)
    monkeypatch.setattr(aio, "economic_calendar", fake_calendar)
    monkeypatch.setattr(aio, "option_series", fake_series)
    monkeypatch.setattr(aio, "history", fake_history)
    monkeypatch.setattr(aio, "research", fake_research)
    monkeypatch.setattr(aio, "corporate_calendar", fake_corporate)
    monkeypatch.setattr(aio, "news_markdown", fake_markdown)
    monkeypatch.setattr(aio, "stream_quotes", fake_stream)

    assert (await search_symbols("Apple"))[0]["description"] == "Apple"
    assert (await get_quote("NASDAQ:AAPL"))["last"] == 200
    assert (await get_quotes(["NASDAQ:AAPL", "NASDAQ:MSFT"]))["NASDAQ:MSFT"] is None
    assert (await query_screener(limit=1))[0]["values"] == {"limit": 1}
    assert (await get_options_chain("NASDAQ:AAPL", 1, "AAPL"))[0]["strike"] == 200
    assert (await get_news("NASDAQ:AAPL", 1))[0]["title"] == "Title"
    assert (await get_economic_calendar("2026-07-22", "2026-07-23", ["US"]))[0][
        "title"
    ] == "Event"
    assert (await get_option_series("NASDAQ:AAPL"))[0]["root"] == "AAPL"
    assert (await get_history("NASDAQ:AAPL"))[0]["close"] == 1.5
    assert (await get_research("NASDAQ:AAPL", "profile"))["section"] == "profile"
    assert (await get_corporate_calendar("earnings"))[0]["category"] == "earnings"
    assert await get_news_markdown("NASDAQ:AAPL") == "# News"
    assert (await get_quote_updates(["NASDAQ:AAPL"]))[0]["last"] == 200
    assert await get_quote_updates(["NASDAQ:AAPL"], updates=0) == []
