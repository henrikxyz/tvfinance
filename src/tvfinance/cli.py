"""Command-line interface with stable JSON output."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from tvfinance import api
from tvfinance.core.models import SerializableModel


def _json_default(value: object) -> object:
    if isinstance(value, SerializableModel):
        return value.to_dict()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _print(value: object) -> None:
    print(json.dumps(value, default=_json_default, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tvfinance")
    parser.add_argument("--version", action="store_true")
    commands = parser.add_subparsers(dest="command")

    search_parser = commands.add_parser("search")
    search_parser.add_argument("query")

    quote_parser = commands.add_parser("quote")
    quote_parser.add_argument("symbol")

    screener_parser = commands.add_parser("screener")
    screener_parser.add_argument("--market", default="america")
    screener_parser.add_argument("--limit", type=int, default=20)

    options_parser = commands.add_parser("options")
    options_parser.add_argument("symbol")
    options_parser.add_argument("--expiration", type=int)
    options_parser.add_argument("--root")

    series_parser = commands.add_parser("option-series")
    series_parser.add_argument("symbol")

    history_parser = commands.add_parser("history")
    history_parser.add_argument("symbol")
    history_parser.add_argument("--resolution", default="1D")
    history_parser.add_argument("--count", default=300, type=_count)

    research_parser = commands.add_parser("research")
    research_parser.add_argument("symbol")
    research_parser.add_argument(
        "section",
        choices=[
            "bonds",
            "etfs",
            "documents",
            "holdings",
            "ideas",
            "financials",
            "forecast",
            "technicals",
            "profile",
        ],
    )

    calendar_parser = commands.add_parser("calendar")
    calendar_parser.add_argument(
        "category", choices=["earnings", "revenue", "dividends", "ipo"]
    )
    calendar_parser.add_argument("--from-date")
    calendar_parser.add_argument("--to-date")
    calendar_parser.add_argument("--limit", type=int, default=100)

    news_parser = commands.add_parser("news")
    news_parser.add_argument("symbol")
    news_parser.add_argument("--limit", type=int, default=10)
    news_parser.add_argument("--body", action="store_true")

    markdown_parser = commands.add_parser("news-markdown")
    markdown_parser.add_argument("symbol")
    markdown_parser.add_argument("--limit", type=int, default=10)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    from tvfinance import __version__

    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    handlers: dict[str, Any] = {
        "search": lambda: api.search(args.query),
        "quote": lambda: api.quote(args.symbol),
        "screener": lambda: api.screener(market=args.market, limit=args.limit),
        "options": lambda: api.options_chain(
            args.symbol, expiration=args.expiration, root=args.root
        ),
        "option-series": lambda: api.option_series(args.symbol),
        "history": lambda: api.history(
            args.symbol,
            resolution=args.resolution,
            count=args.count,
        ),
        "research": lambda: api.research(args.symbol, args.section),
        "calendar": lambda: api.corporate_calendar(
            args.category,
            from_date=_date(args.from_date),
            to_date=_date(args.to_date),
            limit=args.limit,
        ),
        "news": lambda: api.news(args.symbol, limit=args.limit, fetch_body=args.body),
        "news-markdown": lambda: api.news_markdown(args.symbol, limit=args.limit),
    }
    if args.command is None:
        parser.print_help()
        return 0
    _print(handlers[args.command]())
    return 0


def _count(value: str) -> int | str:
    return value if value.lower() == "max" else int(value)


def _date(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None
