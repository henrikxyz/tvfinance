"""Immutable domain models returned by public APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, cast

from tvfinance.core.types import JsonValue


@dataclass(frozen=True, slots=True)
class SerializableModel:
    """Base model with a JSON-compatible dictionary representation."""

    def to_dict(self) -> dict[str, JsonValue]:
        return cast(dict[str, JsonValue], _json_compatible(asdict(self)))


def _json_compatible(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_compatible(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class Symbol(SerializableModel):
    """A fully qualified provider symbol."""

    exchange: str
    name: str

    @property
    def ticker(self) -> str:
        return f"{self.exchange}:{self.name}"

    def __str__(self) -> str:
        return self.ticker


@dataclass(frozen=True, slots=True)
class SymbolSearchResult(SerializableModel):
    """A symbol discovered by a search service."""

    symbol: Symbol
    description: str = ""
    asset_type: str = ""
    currency: str | None = None
    provider_id: str | None = None


@dataclass(frozen=True, slots=True)
class ScreenerRow(SerializableModel):
    """One typed symbol row returned by a market screener."""

    symbol: Symbol
    values: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Quote(SerializableModel):
    """Current quote snapshot."""

    symbol: Symbol
    last: float | None = None
    change: float | None = None
    change_percent: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    previous_close: float | None = None
    volume: float | None = None
    bid: float | None = None
    ask: float | None = None
    currency: str | None = None
    timestamp: datetime | None = None


@dataclass(frozen=True, slots=True)
class Candle(SerializableModel):
    """One OHLCV bar."""

    symbol: Symbol
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


@dataclass(frozen=True, slots=True)
class NewsArticle(SerializableModel):
    """News metadata and optional article body."""

    article_id: str
    title: str
    published_at: datetime
    source: str = ""
    url: str | None = None
    summary: str | None = None
    body_markdown: str | None = None
    symbols: tuple[Symbol, ...] = ()

    def to_markdown(self) -> str:
        """Render the article as portable Markdown."""
        lines = [f"# {self.title}", ""]
        metadata = [f"Source: {self.source}"] if self.source else []
        metadata.append(f"Published: {self.published_at.isoformat()}")
        if self.url:
            metadata.append(f"URL: {self.url}")
        if self.symbols:
            metadata.append("Symbols: " + ", ".join(map(str, self.symbols)))
        lines.extend(metadata)
        if self.summary:
            lines.extend(["", self.summary])
        if self.body_markdown:
            lines.extend(["", self.body_markdown.strip()])
        return "\n".join(lines).strip() + "\n"


@dataclass(frozen=True, slots=True)
class OptionContract(SerializableModel):
    """One call or put option contract."""

    symbol: Symbol
    option_type: str
    strike: float
    expiration: int
    root: str
    bid: float | None = None
    ask: float | None = None
    implied_volatility: float | None = None
    delta: float | None = None
    gamma: float | None = None
    vega: float | None = None
    theta: float | None = None
    rho: float | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class OptionChainRow(SerializableModel):
    """Call and put contracts paired by strike."""

    strike: float
    call: OptionContract | None = None
    put: OptionContract | None = None


@dataclass(frozen=True, slots=True)
class CalendarEvent(SerializableModel):
    """Normalized economic or corporate calendar event."""

    event_id: str
    title: str
    starts_at: datetime
    category: str
    country: str | None = None
    importance: int | None = None
    symbol: Symbol | None = None
    actual: JsonValue = None
    estimate: JsonValue = None
    previous: JsonValue = None
    extra: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResearchData(SerializableModel):
    """Normalized data extracted from one symbol research section."""

    symbol: Symbol
    section: str
    records: tuple[dict[str, JsonValue], ...] = ()
    summary: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OptionSeries(SerializableModel):
    """One selectable option root and expiration combination."""

    root: str
    expiration: int
