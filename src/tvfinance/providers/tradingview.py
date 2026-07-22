"""TradingView HTTP provider adapter."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import cast
from urllib.parse import urljoin

from tvfinance.core.contracts import HttpRequest
from tvfinance.core.exceptions import ParseError, RateLimitError, TransportError
from tvfinance.core.models import (
    CalendarEvent,
    NewsArticle,
    OptionChainRow,
    OptionContract,
    Quote,
    ScreenerRow,
    Symbol,
    SymbolSearchResult,
)
from tvfinance.core.session import AsyncClientSession
from tvfinance.core.types import JsonValue, QueryParams
from tvfinance.core.validation import (
    normalize_symbol,
    normalize_symbols,
    positive_number,
)

SEARCH_URL = "https://symbol-search.tradingview.com/symbol_search/"
NEWS_URL = "https://news-mediator.tradingview.com/public/news-flow/v2/news"
CALENDAR_URL = "https://economic-calendar.tradingview.com/events"
SCANNER_ROOT = "https://scanner.tradingview.com"
SITE_ROOT = "https://www.tradingview.com"

QUOTE_COLUMNS = [
    "close",
    "change",
    "change_abs",
    "open",
    "high",
    "low",
    "Perf.W",
    "volume",
    "bid",
    "ask",
    "currency",
]

OPTION_COLUMNS = [
    "ask",
    "bid",
    "currency",
    "delta",
    "expiration",
    "gamma",
    "iv",
    "option-type",
    "rho",
    "root",
    "strike",
    "theta",
    "vega",
]


class TradingViewProvider:
    """Typed provider operations over an injected client session."""

    def __init__(self, session: AsyncClientSession) -> None:
        self.session = session

    def _headers(self, *, accept: str = "application/json") -> dict[str, str]:
        settings = self.session.settings
        return {
            "Accept": accept,
            "Accept-Language": settings.locale.accept_language,
            "Origin": SITE_ROOT,
            "Referer": f"{SITE_ROOT}/",
            "User-Agent": settings.user_agent,
        }

    async def _json(
        self,
        method: str,
        url: str,
        *,
        params: QueryParams | None = None,
        body: JsonValue = None,
    ) -> JsonValue:
        response = await self.session.request(
            HttpRequest(
                method,
                url,
                headers=self._headers(),
                params=params or {},
                json_body=body,
                timeout=self.session.settings.timeout,
            )
        )
        if response.status_code == 429:
            raise RateLimitError()
        if response.status_code >= 400:
            raise TransportError(
                "Provider request failed",
                status_code=response.status_code,
                context={"method": method, "url": url},
            )
        try:
            return response.json()
        except (UnicodeDecodeError, ValueError) as exc:
            raise ParseError(
                "Provider returned invalid JSON",
                context={"url": url},
            ) from exc

    async def search(self, query: str) -> list[SymbolSearchResult]:
        query = query.strip()
        if not query:
            return []
        data = await self._json(
            "GET",
            SEARCH_URL,
            params={"text": query, "hl": self.session.settings.locale.language},
        )
        rows = _list(data, operation="symbol search")
        results: list[SymbolSearchResult] = []
        for row in rows:
            item = _dict(row, operation="symbol search row")
            exchange = str(item.get("exchange") or "").upper()
            name = str(item.get("symbol") or "").upper()
            if not exchange or not name:
                continue
            results.append(
                SymbolSearchResult(
                    Symbol(exchange, name),
                    description=str(item.get("description") or ""),
                    asset_type=str(item.get("type") or ""),
                    currency=_optional_string(item.get("currency_code")),
                    provider_id=_optional_string(item.get("provider_id")),
                )
            )
        return results

    async def quotes(self, symbols: list[str | Symbol]) -> dict[str, Quote | None]:
        normalized = normalize_symbols(symbols)
        body: JsonValue = {
            "symbols": {"tickers": [item.ticker for item in normalized]},
            "columns": list(QUOTE_COLUMNS),
        }
        data = _dict(
            await self._json("POST", f"{SCANNER_ROOT}/global/scan", body=body),
            operation="quotes",
        )
        result: dict[str, Quote | None] = {item.ticker: None for item in normalized}
        for raw_row in _list(data.get("data", []), operation="quote rows"):
            row = _dict(raw_row, operation="quote row")
            symbol = normalize_symbol(str(row.get("s") or ""))
            values = _list(row.get("d", []), operation="quote values")
            fields = dict(zip(QUOTE_COLUMNS, values, strict=False))
            result[symbol.ticker] = Quote(
                symbol,
                last=_float(fields.get("close")),
                change=_float(fields.get("change_abs")),
                change_percent=_float(fields.get("change")),
                open=_float(fields.get("open")),
                high=_float(fields.get("high")),
                low=_float(fields.get("low")),
                volume=_float(fields.get("volume")),
                bid=_float(fields.get("bid")),
                ask=_float(fields.get("ask")),
                currency=_optional_string(fields.get("currency")),
                timestamp=datetime.now(timezone.utc),
            )
        return result

    async def screener(
        self,
        *,
        market: str = "america",
        columns: list[str] | None = None,
        limit: int = 50,
        sort_by: str = "market_cap_basic",
        sort_order: str = "desc",
    ) -> list[ScreenerRow]:
        positive_number(float(limit), field="limit")
        selected = columns or [
            "ticker-view",
            "close",
            "change",
            "volume",
            "market_cap_basic",
        ]
        body: JsonValue = {
            "columns": cast(JsonValue, selected),
            "range": [0, limit],
            "sort": {"sortBy": sort_by, "sortOrder": sort_order},
            "markets": [] if market in {"crypto", "forex"} else [market],
        }
        data = _dict(
            await self._json("POST", f"{SCANNER_ROOT}/{market}/scan", body=body),
            operation="screener",
        )
        results: list[ScreenerRow] = []
        for raw_row in _list(data.get("data", []), operation="screener rows"):
            row = _dict(raw_row, operation="screener row")
            values = _list(row.get("d", []), operation="screener values")
            mapped = cast(
                dict[str, JsonValue], dict(zip(selected, values, strict=False))
            )
            results.append(ScreenerRow(normalize_symbol(str(row["s"])), mapped))
        return results

    async def options_chain(
        self,
        underlying: str | Symbol,
        *,
        expiration: int,
        root: str,
    ) -> list[OptionChainRow]:
        symbol = normalize_symbol(underlying)
        body: JsonValue = {
            "columns": list(OPTION_COLUMNS),
            "filter2": {
                "operator": "and",
                "operands": [
                    {
                        "expression": {
                            "left": "expiration",
                            "operation": "equal",
                            "right": expiration,
                        }
                    },
                    {
                        "expression": {
                            "left": "root",
                            "operation": "equal",
                            "right": root,
                        }
                    },
                ],
            },
            "index_filters": [{"name": "underlying_symbol", "values": [symbol.name]}],
        }
        data = _dict(
            await self._json(
                "POST",
                f"{SCANNER_ROOT}/options/scan2",
                params={"label-product": "symbols-options"},
                body=body,
            ),
            operation="options",
        )
        fields = [
            str(value)
            for value in _list(
                data.get("fields", cast(JsonValue, OPTION_COLUMNS)), operation="fields"
            )
        ]
        grouped: dict[float, dict[str, OptionContract]] = {}
        for raw_row in _list(data.get("symbols", []), operation="option rows"):
            row = _dict(raw_row, operation="option row")
            values = _list(row.get("f", []), operation="option values")
            item = dict(zip(fields, values, strict=False))
            strike = _float(item.get("strike")) or 0.0
            option_type = str(item.get("option-type") or "call")
            contract = OptionContract(
                normalize_symbol(str(row["s"])),
                option_type,
                strike,
                _integer(item.get("expiration")) or expiration,
                str(item.get("root") or root),
                bid=_float(item.get("bid")),
                ask=_float(item.get("ask")),
                implied_volatility=_float(item.get("iv")),
                delta=_float(item.get("delta")),
                gamma=_float(item.get("gamma")),
                vega=_float(item.get("vega")),
                theta=_float(item.get("theta")),
                rho=_float(item.get("rho")),
                currency=_optional_string(item.get("currency")),
            )
            grouped.setdefault(strike, {})[option_type] = contract
        return [
            OptionChainRow(strike, pair.get("call"), pair.get("put"))
            for strike, pair in sorted(grouped.items())
        ]

    async def news(
        self,
        symbol: str | Symbol,
        *,
        limit: int = 10,
        language: str | None = None,
    ) -> list[NewsArticle]:
        normalized = normalize_symbol(symbol)
        lang = language or self.session.settings.locale.language
        params = [
            ("filter", f"lang:{lang}"),
            ("filter", f"symbol:{normalized.ticker}"),
            ("client", "landing"),
            ("streaming", "false"),
        ]
        data = _dict(await self._json("GET", NEWS_URL, params=params), operation="news")
        results: list[NewsArticle] = []
        for raw_item in _list(data.get("items", []), operation="news items")[:limit]:
            item = _dict(raw_item, operation="news item")
            published = datetime.fromtimestamp(
                _integer(item.get("published")) or 0, tz=timezone.utc
            )
            provider = item.get("provider")
            source = (
                str(provider.get("name") or "") if isinstance(provider, dict) else ""
            )
            story_path = _optional_string(item.get("storyPath"))
            results.append(
                NewsArticle(
                    str(item.get("id") or ""),
                    str(item.get("title") or ""),
                    published,
                    source=source,
                    url=urljoin(SITE_ROOT, story_path) if story_path else None,
                    summary=_optional_string(item.get("description")),
                    symbols=(normalized,),
                )
            )
        return results

    async def economic_calendar(
        self,
        *,
        from_date: datetime,
        to_date: datetime,
        countries: list[str] | None = None,
    ) -> list[CalendarEvent]:
        params: dict[str, str] = {
            "from": from_date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": to_date.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if countries:
            params["countries"] = ",".join(countries)
        data = _dict(
            await self._json("GET", CALENDAR_URL, params=params),
            operation="calendar",
        )
        results: list[CalendarEvent] = []
        for raw_item in _list(data.get("result", []), operation="calendar events"):
            item = _dict(raw_item, operation="calendar event")
            timestamp = datetime.fromisoformat(
                str(item.get("date") or "1970-01-01T00:00:00+00:00").replace(
                    "Z", "+00:00"
                )
            )
            results.append(
                CalendarEvent(
                    str(item.get("id") or ""),
                    str(item.get("title") or ""),
                    timestamp,
                    "economic",
                    country=_optional_string(item.get("country")),
                    importance=_integer(item.get("importance")),
                    actual=_json_value(item.get("actual")),
                    estimate=_json_value(item.get("forecast")),
                    previous=_json_value(item.get("previous")),
                )
            )
        return results


def _dict(value: JsonValue, *, operation: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ParseError(f"Expected an object while parsing {operation}")
    return value


def _list(value: JsonValue, *, operation: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise ParseError(f"Expected a list while parsing {operation}")
    return value


def _float(value: JsonValue) -> float | None:
    if value is None or isinstance(value, bool | list | dict):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: JsonValue) -> int | None:
    number = _float(value)
    return int(number) if number is not None else None


def _optional_string(value: JsonValue) -> str | None:
    return None if value is None else str(value)


def _json_value(value: object) -> JsonValue:
    return cast(JsonValue, value)
