"""Public input normalization and validation."""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime, time, timezone

from tvfinance.core.exceptions import ValidationError
from tvfinance.core.models import Symbol

_SYMBOL_PART = re.compile(r"^[A-Z0-9_!.\-&/]+$")
_LOCALE_PART = re.compile(r"^[A-Za-z]{2,8}$")


def normalize_symbol(value: str | Symbol) -> Symbol:
    """Return a validated uppercase exchange-qualified symbol."""
    if isinstance(value, Symbol):
        return value
    normalized = value.strip().upper()
    if normalized.count(":") != 1:
        raise ValidationError(
            "Symbol must use EXCHANGE:NAME format",
            context={"symbol": normalized},
        )
    exchange, name = normalized.split(":", maxsplit=1)
    if (
        not exchange
        or not name
        or not all(_SYMBOL_PART.fullmatch(part) for part in (exchange, name))
    ):
        raise ValidationError(
            "Symbol contains unsupported characters",
            context={"symbol": normalized},
        )
    return Symbol(exchange=exchange, name=name)


def normalize_symbols(values: Iterable[str | Symbol]) -> tuple[Symbol, ...]:
    """Validate and de-duplicate symbols while preserving input order."""
    unique: dict[str, Symbol] = {}
    for value in values:
        symbol = normalize_symbol(value)
        unique.setdefault(symbol.ticker, symbol)
    if not unique:
        raise ValidationError("At least one symbol is required")
    return tuple(unique.values())


def normalize_locale(language: str, region: str) -> tuple[str, str]:
    """Validate and normalize a language/region pair."""
    if not _LOCALE_PART.fullmatch(language) or not _LOCALE_PART.fullmatch(region):
        raise ValidationError(
            "Locale must contain alphabetic language and region values",
            context={"language": language, "region": region},
        )
    return language.lower(), region.upper()


def ensure_utc(value: date | datetime) -> datetime:
    """Convert a date or datetime into a timezone-aware UTC datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def positive_number(value: float, *, field: str) -> float:
    """Require a positive numeric configuration value."""
    if value <= 0:
        raise ValidationError(
            f"{field} must be greater than zero",
            context={"field": field, "value": value},
        )
    return value
