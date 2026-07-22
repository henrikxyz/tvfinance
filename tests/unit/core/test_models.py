from __future__ import annotations

from datetime import datetime, timezone

from tvfinance.core import (
    CalendarEvent,
    Candle,
    NewsArticle,
    OptionChainRow,
    OptionContract,
    Quote,
    Symbol,
    SymbolSearchResult,
)


def test_symbol_identity() -> None:
    symbol = Symbol("NASDAQ", "AAPL")
    assert symbol.ticker == "NASDAQ:AAPL"
    assert str(symbol) == "NASDAQ:AAPL"


def test_models_serialize_nested_values_and_datetimes() -> None:
    moment = datetime(2026, 7, 22, tzinfo=timezone.utc)
    symbol = Symbol("NASDAQ", "AAPL")
    contract = OptionContract(symbol, "call", 200.0, 20261218, "AAPL")
    models = [
        SymbolSearchResult(symbol, "Apple", "stock", "USD", "ice"),
        Quote(symbol, last=200.0, timestamp=moment),
        Candle(symbol, moment, 1.0, 2.0, 0.5, 1.5, 100.0),
        NewsArticle("n1", "Title", moment, symbols=(symbol,)),
        OptionChainRow(200.0, call=contract),
        CalendarEvent("e1", "Event", moment, "economic", actual={"value": 1}),
    ]

    serialized = [model.to_dict() for model in models]
    assert serialized[1]["timestamp"] == "2026-07-22T00:00:00+00:00"
    assert serialized[3]["symbols"] == [{"exchange": "NASDAQ", "name": "AAPL"}]
    assert serialized[4]["call"] == contract.to_dict()
    assert serialized[5]["actual"] == {"value": 1}
