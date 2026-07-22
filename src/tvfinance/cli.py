"""Command-line interface with stable JSON output."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
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
    options_parser.add_argument("--expiration", required=True, type=int)
    options_parser.add_argument("--root", required=True)

    news_parser = commands.add_parser("news")
    news_parser.add_argument("symbol")
    news_parser.add_argument("--limit", type=int, default=10)
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
        "news": lambda: api.news(args.symbol, limit=args.limit),
    }
    if args.command is None:
        parser.print_help()
        return 0
    _print(handlers[args.command]())
    return 0
