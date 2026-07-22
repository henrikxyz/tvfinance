"""Object-oriented symbol facade."""

from __future__ import annotations

from tvfinance.client import Client
from tvfinance.core.models import NewsArticle, OptionChainRow, Quote, Symbol
from tvfinance.core.validation import normalize_symbol


class Ticker:
    """Bind repeated operations to one validated symbol."""

    def __init__(self, symbol: str | Symbol, *, client: Client | None = None) -> None:
        self.symbol = normalize_symbol(symbol)
        self.client = client or Client()

    def quote(self) -> Quote:
        return self.client.quote(self.symbol)

    def news(
        self, *, limit: int = 10, language: str | None = None
    ) -> list[NewsArticle]:
        return self.client.news(self.symbol, limit=limit, language=language)

    def options_chain(
        self, *, expiration: int, root: str | None = None
    ) -> list[OptionChainRow]:
        return self.client.options_chain(
            self.symbol,
            expiration=expiration,
            root=root or self.symbol.name,
        )
