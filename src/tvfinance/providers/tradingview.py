"""TradingView HTTP provider adapter."""

from __future__ import annotations

import secrets
import time
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import cast
from urllib.parse import urljoin

from tvfinance.core.contracts import HttpRequest
from tvfinance.core.exceptions import ParseError, RateLimitError, TransportError
from tvfinance.core.history import fetch_history
from tvfinance.core.models import (
    CalendarEvent,
    Candle,
    NewsArticle,
    OptionChainRow,
    OptionContract,
    OptionSeries,
    Quote,
    ResearchData,
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
from tvfinance.core.websocket import decode_methods, encode_method
from tvfinance.providers.research import (
    RESEARCH_SLUGS,
    article_html_to_markdown,
    parse_research_html,
    research_url,
)

SEARCH_URL = "https://symbol-search.tradingview.com/symbol_search/"
NEWS_URL = "https://news-mediator.tradingview.com/public/news-flow/v2/news"
CALENDAR_URL = "https://economic-calendar.tradingview.com/events"
SCANNER_ROOT = "https://scanner.tradingview.com"
SITE_ROOT = "https://www.tradingview.com"
WEBSOCKET_URL = "wss://data.tradingview.com/socket.io/websocket"

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

    async def _text(self, url: str) -> str:
        response = await self.session.request(
            HttpRequest(
                "GET",
                url,
                headers=self._headers(accept="text/html"),
                timeout=self.session.settings.timeout,
            )
        )
        if response.status_code >= 400:
            raise TransportError(
                "Provider page request failed",
                status_code=response.status_code,
                context={"url": url},
            )
        try:
            return response.text
        except UnicodeDecodeError as exc:
            raise ParseError("Provider page is not valid UTF-8") from exc

    async def history(
        self,
        symbol: str | Symbol,
        *,
        resolution: str = "1D",
        count: int | str | None = None,
        adjustment: str = "splits",
    ) -> list[Candle]:
        normalized = normalize_symbol(symbol)
        socket = await self.session.open_websocket(
            WEBSOCKET_URL, headers=self._headers(accept="*/*")
        )
        try:
            return await fetch_history(
                socket,
                normalized,
                resolution=resolution,
                count=count,
                adjustment=adjustment,
                timeout=self.session.settings.timeout,
            )
        finally:
            await socket.close()

    async def option_series(self, symbol: str | Symbol) -> list[OptionSeries]:
        normalized = normalize_symbol(symbol)
        socket = await self.session.open_websocket(
            WEBSOCKET_URL, headers=self._headers(accept="*/*")
        )
        session_id = f"qs_{secrets.token_hex(6)}"
        calls: list[tuple[str, list[JsonValue]]] = [
            ("set_auth_token", ["unauthorized_user_token"]),
            ("quote_create_session", [session_id]),
            ("quote_set_fields", [session_id, "options-info"]),
            ("quote_add_symbols", [session_id, normalized.ticker]),
        ]
        try:
            for method, call_params in calls:
                await socket.send_text(encode_method(method, call_params))
            deadline = time.monotonic() + self.session.settings.timeout
            buffer = ""
            while time.monotonic() < deadline:
                buffer += await socket.receive_text(
                    timeout=max(0.1, deadline - time.monotonic())
                )
                messages, buffer = decode_methods(buffer)
                for message in messages:
                    msg_params = message.get("p")
                    if message.get("m") != "qsd" or not isinstance(msg_params, list):
                        continue
                    if len(msg_params) < 2 or not isinstance(msg_params[1], dict):
                        continue
                    values = msg_params[1].get("v")
                    if not isinstance(values, dict):
                        continue
                    info = values.get("options-info")
                    if info is not None:
                        return _option_series(info)
            raise TransportError(
                "Option metadata timed out",
                retryable=True,
                context={"symbol": normalized.ticker},
            )
        finally:
            await socket.close()

    async def research(self, symbol: str | Symbol, section: str) -> ResearchData:
        normalized = normalize_symbol(symbol)
        if section not in RESEARCH_SLUGS:
            raise ParseError(
                "Unsupported research section", context={"section": section}
            )
        markup = await self._text(research_url(normalized, section))
        return parse_research_html(markup, normalized, section)

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

    async def stream_quotes(self, symbols: list[str | Symbol]) -> AsyncIterator[Quote]:
        """Yield live quote updates until the consumer stops iteration."""
        normalized = normalize_symbols(symbols)
        socket = await self.session.open_websocket(
            WEBSOCKET_URL, headers=self._headers(accept="*/*")
        )
        session_id = f"qs_{secrets.token_hex(6)}"
        fields = ["lp", "ch", "chp", "volume", "bid", "ask", "currency_code", "rtc"]
        calls: list[tuple[str, list[JsonValue]]] = [
            ("set_auth_token", ["unauthorized_user_token"]),
            ("quote_create_session", [session_id]),
            ("quote_set_fields", [session_id, *fields]),
            ("quote_add_symbols", [session_id, *[item.ticker for item in normalized]]),
        ]
        buffer = ""
        try:
            for method, params in calls:
                await socket.send_text(encode_method(method, params))
            while True:
                chunk = await socket.receive_text(timeout=self.session.settings.timeout)
                if chunk.startswith("~h~"):
                    await socket.send_text(chunk)
                    continue
                buffer += chunk
                messages, buffer = decode_methods(buffer)
                for message in messages:
                    msg_params = message.get("p")
                    if message.get("m") != "qsd" or not isinstance(msg_params, list):
                        continue
                    if len(msg_params) < 2 or not isinstance(msg_params[1], dict):
                        continue
                    update = msg_params[1]
                    values = update.get("v")
                    raw_symbol = update.get("n")
                    if not isinstance(values, dict) or not isinstance(raw_symbol, str):
                        continue
                    quote_symbol = normalize_symbol(raw_symbol)
                    timestamp = _float(values.get("rtc"))
                    yield Quote(
                        quote_symbol,
                        last=_float(values.get("lp")),
                        change=_float(values.get("ch")),
                        change_percent=_float(values.get("chp")),
                        volume=_float(values.get("volume")),
                        bid=_float(values.get("bid")),
                        ask=_float(values.get("ask")),
                        currency=_optional_string(values.get("currency_code")),
                        timestamp=(
                            datetime.fromtimestamp(timestamp, tz=timezone.utc)
                            if timestamp is not None
                            else datetime.now(timezone.utc)
                        ),
                    )
        finally:
            await socket.close()

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
        fetch_body: bool = False,
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
            body = None
            url = urljoin(SITE_ROOT, story_path) if story_path else None
            if fetch_body and url:
                try:
                    body = article_html_to_markdown(
                        await self._text(url), title=str(item.get("title") or "")
                    )
                except TransportError:
                    body = None
            results.append(
                NewsArticle(
                    str(item.get("id") or ""),
                    str(item.get("title") or ""),
                    published,
                    source=source,
                    url=url,
                    summary=_optional_string(item.get("description")),
                    body_markdown=body,
                    symbols=(normalized,),
                )
            )
        return results

    async def corporate_calendar(
        self,
        category: str,
        *,
        from_date: datetime,
        to_date: datetime,
        limit: int = 100,
    ) -> list[CalendarEvent]:
        configurations = {
            "earnings": (
                "earnings_release_date,earnings_release_next_date",
                [
                    "name",
                    "description",
                    "earnings_release_date",
                    "earnings_release_next_date",
                    "earnings_per_share_fq",
                    "earnings_per_share_forecast_fq",
                    "revenue_fq",
                    "revenue_forecast_fq",
                ],
            ),
            "revenue": (
                "earnings_release_date,earnings_release_next_date",
                [
                    "name",
                    "description",
                    "earnings_release_date",
                    "revenue_fq",
                    "revenue_forecast_fq",
                    "revenue_surprise_fq",
                ],
            ),
            "dividends": (
                "dividend_ex_date_recent,dividend_ex_date_upcoming",
                [
                    "name",
                    "description",
                    "dividend_ex_date_recent",
                    "dividend_ex_date_upcoming",
                    "dividend_amount_recent",
                    "dividend_amount_upcoming",
                    "dividends_yield",
                ],
            ),
            "ipo": (
                "ipo_offer_time",
                [
                    "name",
                    "description",
                    "ipo_offer_time",
                    "ipo_offer_price_usd",
                    "ipo_offer_status",
                    "ipo_offered_shares",
                    "ipo_deal_amount_usd",
                ],
            ),
        }
        if category not in configurations:
            raise ParseError(
                "Unsupported calendar category", context={"category": category}
            )
        date_field, columns = configurations[category]
        body: JsonValue = {
            "filter": [
                {
                    "left": date_field,
                    "operation": "in_range",
                    "right": [from_date.timestamp(), to_date.timestamp()],
                }
            ],
            "columns": cast(JsonValue, columns),
            "range": [0, limit],
            "options": {"lang": self.session.settings.locale.language},
        }
        data = _dict(
            await self._json(
                "POST",
                f"{SCANNER_ROOT}/global/scan",
                params={"label-product": f"calendar-{category}"},
                body=body,
            ),
            operation=f"{category} calendar",
        )
        events: list[CalendarEvent] = []
        for raw in _list(data.get("data", []), operation=f"{category} rows"):
            row = _dict(raw, operation=f"{category} row")
            values = _list(row.get("d", []), operation=f"{category} values")
            mapped = dict(zip(columns, values, strict=False))
            timestamp = next(
                (
                    _float(mapped.get(field))
                    for field in date_field.split(",")
                    if _float(mapped.get(field)) is not None
                ),
                None,
            )
            if timestamp is None:
                continue
            event_symbol = normalize_symbol(str(row.get("s") or ""))
            events.append(
                CalendarEvent(
                    str(row.get("s") or ""),
                    str(
                        mapped.get("description")
                        or mapped.get("name")
                        or event_symbol.name
                    ),
                    datetime.fromtimestamp(timestamp, tz=timezone.utc),
                    category,
                    symbol=event_symbol,
                    extra=mapped,
                )
            )
        return events

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


def _option_series(value: JsonValue) -> list[OptionSeries]:
    """Flatten provider option metadata without depending on one schema revision."""
    found: set[tuple[str, int]] = set()

    def visit(item: JsonValue, root: str | None = None) -> None:
        if isinstance(item, dict):
            current_root = str(item.get("root") or item.get("name") or root or "")
            expiration = _integer(item.get("expiration") or item.get("expiry"))
            if current_root and expiration:
                found.add((current_root, expiration))
            for nested in item.values():
                visit(nested, current_root)
        elif isinstance(item, list):
            for nested in item:
                visit(nested, root)
        elif root:
            expiration = _integer(item)
            if expiration and expiration > 10_000_000:
                found.add((root, expiration))

    visit(value)
    return [OptionSeries(root, expiration) for root, expiration in sorted(found)]
