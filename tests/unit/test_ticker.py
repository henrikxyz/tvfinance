from __future__ import annotations

from typing import Any, cast

from tvfinance import Ticker


class FakeClient:
    def quote(self, symbol: object) -> str:
        return str(symbol)

    def news(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs

    def options_chain(self, symbol: object, **kwargs: Any) -> Any:
        return symbol, kwargs


def test_ticker_binds_symbol_and_defaults_option_root() -> None:
    ticker = Ticker("nasdaq:aapl", client=FakeClient())  # type: ignore[arg-type]
    untyped = cast(Any, ticker)
    assert untyped.quote() == "NASDAQ:AAPL"
    assert untyped.news(limit=2)[1]["limit"] == 2
    assert untyped.options_chain(expiration=1)[1]["root"] == "AAPL"
    assert untyped.options_chain(expiration=1, root="X")[1]["root"] == "X"
